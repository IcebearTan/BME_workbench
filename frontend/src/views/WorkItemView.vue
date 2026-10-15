<script setup>
// 事项详情页（话题/任务同构，§6.2）：顶部=标题/归属组/可见范围/状态/动作区；
// 主体=说明（Markdown）+ 单层回复时间线；操作记录独立区块区分「系统确认发生了什么」。
// 回复按服务器序号游标增量轮询（§7.5 活动页 30s、隐藏页暂停）；打开即推进已读游标。
// 撤权后的历史通知点击 → 404 → 统一「内容不可访问」空态（§10.2 不泄露）。
// 工作台 III：chrome 由外壳 WorkShell 承载，此处只渲染内容区。
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useStore } from 'vuex'
import { ElMessage } from 'element-plus'
import { MdPreview } from 'md-editor-v3'
import 'md-editor-v3/lib/preview.css'
import '@bme/editor/md-setup'
import { DewCard, DewTag, DewSkeleton, DewButton } from '@bme/dew-ui'
import { ArrowLeft, Lock } from '@element-plus/icons-vue'
import WorkReplyComposer from '../components/Work/WorkReplyComposer.vue'
import WorkEventTrail from '../components/Work/WorkEventTrail.vue'
import WorkParticipantDialog from '../components/Work/WorkParticipantDialog.vue'
import WorkTaskPanel from '../components/Work/WorkTaskPanel.vue'
import WorkFileList from '../components/Work/WorkFileList.vue'
import WorkBusinessCard from '../components/Work/WorkBusinessCard.vue'
import WorkCommandBar from '../components/Work/WorkCommandBar.vue'
import WorkItemSettingsDialog from '../components/Work/WorkItemSettingsDialog.vue'
import WorkCollaborationPanel from '../components/Work/WorkCollaborationPanel.vue'
import { useWorkAccess } from '../composables/useWorkAccess'
import { workService, ITEM_STATUS_LABELS, ITEM_STATUS_TYPE, VISIBILITY_LABELS } from '../services/workService'

const PREVIEW_ID = 'work-item-preview'
const route = useRoute()
const router = useRouter()
const store = useStore()
const isDarkMode = computed(() => store.getters.isDarkMode)

const itemId = computed(() => Number(route.params.id))
const { me: workMe } = useWorkAccess()
const workTargets = computed(() => (workMe.value?.available_targets || []).filter(w => w.ws_id !== detail.value?.workspace_id))

// ── 数据态（三段式） ──
const detail = ref(null)
const replies = ref([])
const repliesHasMore = ref(false)   // 超过一页（50 条）时分批「加载更多」，不自动拉全
const loadingMore = ref(false)
const loading = ref(true)
const loadFailed = ref(false)
const notAccessible = ref(false)
let loadGeneration = 0

const inviteVisible = ref(false)
const replyTo = ref(null)
const pendingRequest = ref(null)

const settingsVisible = ref(false)
const commandBar = ref(null)
const collaborationPanel = ref(null)

const allowed = computed(() => detail.value?.allowed_actions || [])
const draftNeedsSettings = computed(() => detail.value?.kind === 'task' && detail.value.status === 'draft'
  && (!detail.value.task?.assignee_user_id || !detail.value.task?.due_at))
const hiddenCommands = computed(() => ['handoff', ...(draftNeedsSettings.value ? ['publish'] : [])])
const canReply = computed(() =>
  detail.value && detail.value.status !== 'closed' && detail.value.status !== 'draft')
const responders = computed(() => {
  if (!detail.value) return []
  const list = (detail.value.participants || []).map(p => ({ user_id: p.user_id, username: p.username }))
  if (!list.some(r => r.user_id === detail.value.created_by)) {
    list.unshift({ user_id: detail.value.created_by, username: detail.value.created_by_name })
  }
  return list.filter(r => r.user_id !== store.state.user?.User_Id)
})

async function loadDetail() {
  const id = itemId.value
  const generation = loadGeneration
  const res = await workService.fetchItem(id)
  if (itemId.value !== id || generation !== loadGeneration) return
  detail.value = res.data
}

async function loadReplies(afterSeq = 0) {
  const id = itemId.value
  const generation = loadGeneration
  const res = await workService.fetchReplies(id, { after_seq: afterSeq, limit: 50 })
  if (itemId.value !== id || generation !== loadGeneration) return {}
  const data = res.data || {}
  if (afterSeq === 0) {
    replies.value = data.replies || []
  } else if (data.replies?.length) {
    // 回包按 id merge：同 id 的占位行被真实行替换（发送后的空正文占位即在此兑现）
    const byId = new Map(replies.value.map(r => [r.id, r]))
    for (const r of data.replies) byId.set(r.id, r)
    replies.value = [...byId.values()].sort((a, b) => a.seq - b.seq)
  }
  repliesHasMore.value = Boolean(data.has_more)
  return data
}

async function loadMoreReplies() {
  if (!replies.value.length || loadingMore.value) return
  loadingMore.value = true
  try {
    await loadReplies(replies.value[replies.value.length - 1].seq)
  } catch {
    ElMessage.error('回复加载失败，请重试')
  } finally {
    loadingMore.value = false
  }
}

async function loadPendingRequest() {
  const id = itemId.value
  const generation = loadGeneration
  try {
    const res = await workService.fetchTodos()
    if (itemId.value !== id || generation !== loadGeneration) return
    pendingRequest.value = (res.data?.pending_responses || [])
      .find(r => r.item_id === id) || null
  } catch { if (itemId.value === id && generation === loadGeneration) pendingRequest.value = null }
}

async function advanceRead(seq, id = itemId.value) {
  if (!seq) return
  try {
    await workService.advanceRead(id, seq)
  } catch { /* 游标推进失败不影响阅读 */ }
}

async function loadAll() {
  const generation = ++loadGeneration
  loading.value = true
  loadFailed.value = false
  notAccessible.value = false
  // allSettled 不 reject：逐个检查结果，404=不可访问、其他失败=loadFailed（可重试），
  // 不再把网络错误/500 误报成「撤权」
  const results = await Promise.allSettled([loadDetail(), loadReplies(0), loadPendingRequest()])
  if (generation !== loadGeneration) return
  const rejected = results.find(r => r.status === 'rejected')
  if (rejected) {
    if (rejected.reason?.response?.status === 404) {
      notAccessible.value = true
    } else {
      loadFailed.value = true
    }
  } else if (!detail.value) {
    notAccessible.value = true
  } else {
    // 打开即推进已读（到当前最新回复）
    advanceRead(detail.value.last_reply_seq)
  }
  loading.value = false
}

// 事项→事项导航（如铃铛里点另一条 work 通知）：重置页面态并重载，不停轮询
watch(itemId, (id, oldId) => {
  if (!id || Number.isNaN(id) || id === oldId) return
  detail.value = null
  replies.value = []
  repliesHasMore.value = false
  pendingRequest.value = null
  replyTo.value = null
  settingsVisible.value = false
  inviteVisible.value = false
  loadAll()
})

// ── 增量轮询：活动页 30s，隐藏页暂停（§7.5） ──
let pollTimer = null
function startPolling() {
  if (pollTimer) return
  pollTimer = setInterval(async () => {
    if (document.visibilityState !== 'visible' || !detail.value) return
    const id = itemId.value
    const generation = loadGeneration
    try {
      const data = await loadReplies(replies.value.length ? replies.value[replies.value.length - 1].seq : 0)
      if (id !== itemId.value || generation !== loadGeneration || !detail.value) return
      if (data.last_reply_seq > (detail.value.last_read_seq || 0)) {
        advanceRead(data.last_reply_seq, id)
        detail.value.last_read_seq = data.last_reply_seq
      }
    } catch { /* 轮询失败静默，下轮重试 */ }
  }, 30000)
}
function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

// ── 动作 ──
// 命令类操作由 WorkCommandBar 统一执行，完成后 refreshAll（重新拉详情+回复）
async function refreshAll() {
  const id = itemId.value
  const generation = loadGeneration
  const results = await Promise.allSettled([loadDetail(), loadReplies(0), collaborationPanel.value?.refresh()])
  if (id !== itemId.value || generation !== loadGeneration) return
  if (results.some(result => result.status === 'rejected' && result.reason?.response?.status === 404)) {
    detail.value = null
    replies.value = []
    notAccessible.value = true
    settingsVisible.value = false
    inviteVisible.value = false
    return
  }
  if (results.some(result => result.status === 'rejected')) ElMessage.warning('部分内容刷新失败，请重新打开查看最新状态')
}

function onReplySent(reply) {
  const id = itemId.value
  const generation = loadGeneration
  // 占位行仅携带定位信息；真实正文由 loadReplies 回包按 id merge 替换（见 loadReplies）
  replies.value.push({
    id: reply.id, seq: reply.seq,
    author_id: store.state.user?.User_Id,
    author_name: store.state.user?.User_Name,
    body: '',
    reply_to_id: replyTo.value?.id || null,
    created_at: '刚刚',
  })
  replyTo.value = null
  pendingRequest.value = null
  loadReplies(replies.value[replies.value.length - 1].seq - 1).then(() => {
    if (detail.value && id === itemId.value && generation === loadGeneration) {
      detail.value.last_reply_seq = Math.max(detail.value.last_reply_seq, reply.seq)
      advanceRead(reply.seq)
    }
  })
}

// ── 引用锚点：#seq 可点击，滚动定位到被引用回复并高亮 ──
function quotedSeq(id) {
  return (replies.value.find(x => x.id === id) || {}).seq || '?'
}
function scrollToReply(id) {
  const el = document.querySelector(`[data-reply-id="${id}"]`)
  if (!el) return
  el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  el.classList.remove('reply-row--flash')
  // 强制重排以重启动画
  void el.offsetWidth
  el.classList.add('reply-row--flash')
}

onMounted(() => {
  loadAll()
  startPolling()
})
onUnmounted(stopPolling)
</script>

<template>
  <div class="work-item-view">
    <!-- 骨架 -->
    <template v-if="loading">
      <DewSkeleton variant="rect" :height="26" :width="260" class="sk-block" />
      <DewCard size="md" class="sk-block"><DewSkeleton variant="text" :lines="4" /></DewCard>
      <DewCard size="md"><DewSkeleton variant="text" :lines="6" /></DewCard>
    </template>

    <!-- 不可访问（含撤权后的历史通知点击，§10.2） -->
    <DewCard v-else-if="notAccessible" size="md" variant="flat" class="state-card">
      <h3 class="state-title">内容不可访问</h3>
      <p class="state-text">该事项不存在、已被移除，或你当前没有访问权限。</p>
      <DewButton size="sm" @click="router.push('/work')">返回工作台</DewButton>
    </DewCard>

    <!-- 失败态 -->
    <DewCard v-else-if="loadFailed" size="md" variant="flat" class="state-card">
      <p class="state-text">加载失败，请稍后重试</p>
      <DewButton size="sm" @click="loadAll">重试</DewButton>
    </DewCard>

    <template v-else-if="detail">
      <!-- 头部：标题/元信息/动作区 -->
      <DewCard size="md" variant="flat" class="head-card">
        <div class="back-row">
          <DewButton type="ghost" size="sm" @click="router.back()">
            <el-icon :size="13"><ArrowLeft /></el-icon>
            返回
          </DewButton>
        </div>
        <div class="title-line">
          <h1 class="item-title">{{ detail.title }}</h1>
          <DewTag :type="ITEM_STATUS_TYPE[detail.status] || 'neutral'" size="sm" round>
            {{ ITEM_STATUS_LABELS[detail.status] || detail.status }}
          </DewTag>
        </div>
        <div class="meta-line">
          <span>{{ detail.group_name }}</span>
          <span class="meta-visibility">
            <el-icon :size="12"><Lock /></el-icon>
            {{ VISIBILITY_LABELS[detail.visibility] || detail.visibility }}
          </span>
          <span>发起：{{ detail.created_by_name }}</span>
          <span>{{ detail.created_at }}</span>
          <span>回复 {{ detail.reply_count }}</span>
        </div>
        <!-- 动作区（allowed_actions 驱动；后端每次仍重新授权 §13） -->
        <div v-if="allowed.length" class="action-line">
          <DewButton v-if="allowed.includes('edit')" size="sm" @click="settingsVisible = true">事项设置</DewButton>
        </div>
        <div v-if="detail.status === 'draft'" class="draft-guidance">
          <span>{{ draftNeedsSettings ? '已保存为仅你可见的草稿。在事项设置中补齐负责人和截止时间，即可发布。' : '当前仅你可见。发布后可开始讨论，并邀请其他组成员。' }}</span>
          <DewButton v-if="draftNeedsSettings && allowed.includes('edit')" size="sm" active @click="settingsVisible = true">完善任务设置</DewButton>
        </div>
        <WorkCommandBar ref="commandBar" :key="itemId" :item-id="itemId" :kind="detail.kind" :version="detail.version"
                        :allowed="allowed" :files="detail.files || []"
                        :targets="workTargets" :hidden-actions="hiddenCommands" @done="refreshAll" />
        <div v-if="detail.status === 'closed' && detail.closed_reason" class="closed-reason">
          关闭说明：{{ detail.closed_reason }}
        </div>
      </DewCard>

      <!-- 关联对象（X2 通用投影：盲渲染适配器字段） -->
      <WorkBusinessCard :item-id="itemId" :links="detail.business_links || []"
                        :can-manage="allowed.includes('edit') || allowed.includes('invite')"
                        @changed="loadDetail" />

      <!-- 任务属性与提交历史 -->
      <WorkTaskPanel :detail="detail" />

      <WorkCollaborationPanel ref="collaborationPanel" :key="itemId" :item="detail"
                              @invite="inviteVisible = true" @handoff="commandBar?.openCommand('handoff')"
                              @promote="commandBar?.openCommand('promote')" @changed="refreshAll" />

      <!-- 正文（flat：阅读场景纯色容器） -->
      <DewCard v-if="detail.body" size="md" variant="flat" class="body-card">
        <MdPreview :id="PREVIEW_ID" :model-value="detail.body" :theme="isDarkMode ? 'dark' : 'light'" />
      </DewCard>

      <!-- 附件区（文件属于事项；版本不可覆盖） -->
      <WorkFileList :item-id="itemId" :files="detail.files || []"
                    :can-upload="detail.status !== 'draft'" @changed="loadDetail" />

      <!-- 回复时间线（单层 + 引用） -->
      <DewCard size="md" variant="flat" class="replies-card">
        <div class="replies-title">讨论（{{ replies.filter(r => !r.removed).length }}）</div>
        <div class="reply-list">
          <div v-for="r in replies" :key="r.id" :data-reply-id="r.id"
               class="reply-row" :class="{ 'reply-row--removed': r.removed }">
            <div v-if="r.removed" class="reply-removed">该回复已被撤回</div>
            <template v-else>
              <div class="reply-head">
                <span class="reply-author">{{ r.author_name }}</span>
                <span v-if="r.edited_at" class="reply-edited">已编辑</span>
                <span class="reply-time">#{{ r.seq }} · {{ r.created_at }}</span>
                <div class="spacer" />
                <DewButton v-if="canReply && r.author_id !== store.state.user?.User_Id"
                           type="ghost" size="sm" @click="replyTo = r">引用</DewButton>
              </div>
              <button v-if="r.reply_to_id" type="button" class="reply-quote"
                      @click="scrollToReply(r.reply_to_id)">
                引用 #{{ quotedSeq(r.reply_to_id) }}
              </button>
              <p class="reply-body">{{ r.body }}</p>
            </template>
          </div>
          <p v-if="!replies.length" class="reply-empty">还没有回复</p>
          <!-- 超过一页时分批加载（不自动拉全，控制首屏与请求量） -->
          <DewButton v-if="repliesHasMore" size="sm" class="load-more-btn"
                     :loading="loadingMore" @click="loadMoreReplies">
            加载更多回复
          </DewButton>
        </div>

        <WorkReplyComposer v-if="canReply" :key="itemId" :item-id="itemId" :responders="responders"
                           :reply-to="replyTo" :pending-request="pendingRequest"
                           @sent="onReplySent" @cancel-quote="replyTo = null" />
        <p v-else-if="detail.status === 'closed'" class="reply-closed-hint">
          话题已关闭，停止普通回复；如需继续讨论请协调员重新打开
        </p>
        <p v-else-if="detail.status === 'draft'" class="reply-closed-hint">
          草稿发布后才能开始讨论
        </p>
      </DewCard>

      <!-- 操作记录（与讨论区分呈现，§6.2） -->
      <WorkEventTrail :key="itemId" :item-id="itemId" />
    </template>

    <WorkParticipantDialog :key="itemId" v-model="inviteVisible" :item-id="itemId"
                           :existing="[detail?.created_by, ...(detail?.participants || []).map(p => p.user_id)]"
                           @invited="refreshAll" />
    <WorkItemSettingsDialog v-if="detail" :key="itemId" v-model="settingsVisible" :item="detail" @saved="refreshAll" />
  </div>
</template>

<style scoped>
.work-item-view { max-width: 860px; }
.draft-guidance { margin-top: 12px; padding: 12px; background: var(--el-fill-color-light); border-radius: 8px; display: flex; flex-wrap: wrap; gap: 10px; align-items: center; font-size: 13px; line-height: 1.7; }

.sk-block { margin-bottom: 14px; }

.back-row { margin-bottom: 6px; }
.title-line { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.item-title { font-size: 20px; font-weight: 700; margin: 0; }
.meta-line {
  display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
  margin-top: 8px; font-size: 12.5px; color: var(--dew-text-muted);
}
.meta-visibility { display: inline-flex; align-items: center; gap: 3px; }
.action-line { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }
.closed-reason {
  margin-top: 10px; padding: 8px 12px; border-radius: 8px; font-size: 12.5px;
  color: var(--dew-text-muted);
  background: var(--dew-card-flat-bg);
}

.body-card { margin-top: 14px; }
.replies-card { margin-top: 14px; }
.replies-title { font-size: 14px; font-weight: 600; margin-bottom: 10px; }

.reply-row { padding: 10px 0; border-bottom: 1px dashed var(--el-border-color-lighter); }
.reply-row:last-of-type { border-bottom: none; }
.reply-head { display: flex; align-items: center; gap: 8px; }
.reply-author { font-size: 13px; font-weight: 600; }
.reply-edited { font-size: 11px; color: var(--dew-text-faint); }
.reply-time { font-size: 12px; color: var(--dew-text-muted); }
.spacer { flex: 1; }
/* 引用锚点：可点击跳转到被引用回复（hover 用形态反馈） */
.reply-quote {
  display: block;
  margin: 6px 0; padding: 4px 10px; border: none; border-left: 2px solid var(--el-border-color);
  font-size: 12px; color: var(--dew-text-muted); font-family: inherit;
  background: transparent; cursor: pointer; text-align: left;
  border-radius: 0 6px 6px 0;
  transition: transform 0.2s ease, background 0.2s ease;
}
.reply-quote:hover {
  transform: translateX(2px);
  background: color-mix(in srgb, var(--color-primary) 6%, transparent);
}
.reply-body { margin: 6px 0 0; font-size: 13.5px; line-height: 1.8; white-space: pre-wrap; word-break: break-word; }
.reply-row--removed .reply-removed { font-size: 12.5px; color: var(--dew-text-muted); font-style: italic; }
.reply-empty, .reply-closed-hint { font-size: 13px; color: var(--dew-text-muted); padding: 8px 0; }
.load-more-btn { margin: 10px 0; }
/* 锚点定位高亮：一次性脉冲后回落 */
.reply-row--flash { animation: replyFlash 1.6s ease-out; }
@keyframes replyFlash {
  0% { background: color-mix(in srgb, var(--color-primary) 12%, transparent); }
  100% { background: transparent; }
}

.state-card { max-width: 480px; margin: 40px auto 0; text-align: center; }
.state-title { margin: 0 0 8px; font-size: 17px; font-weight: 600; }
.state-text { margin: 0 0 12px; font-size: 13px; color: var(--dew-text-muted); }
</style>
