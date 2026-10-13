<script setup>
// 概览仪表盘（工作台 III，外壳子路由默认着陆）＝待办中心：
// 数字块（五桶计数，点击锚点跳桶）→ 行动桶区（待接单/待接手/待回复/待验收，行内操作）
// → 双列信息区（左：即将到期；右：最近活动）。
// 资格探测与摘要轮询由外壳 WorkShell 持有；此处拉待办明细与最近活动。
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { DewCard, DewSkeleton, DewButton } from '@bme/dew-ui'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useWorkData } from '../composables/useWorkData'
import { workService } from '../services/workService'

const router = useRouter()
const { todoCounts, refreshSummary } = useWorkData()

// ── 数字块（徽标口径=摘要五桶，与侧栏「概览」badge 同源；点击锚点跳对应桶） ──
const statBlocks = computed(() => [
  { key: 'pending_responses', label: '待回复', value: todoCounts.value.pending_responses || 0, bucket: 'bucket-responses' },
  { key: 'pending_transfers', label: '待接手', value: todoCounts.value.pending_transfers || 0, bucket: 'bucket-transfers' },
  { key: 'to_review', label: '待验收', value: todoCounts.value.to_review || 0, bucket: 'bucket-review' },
  { key: 'due_soon', label: '即将到期', value: todoCounts.value.due_soon || 0, bucket: 'bucket-due' },
  { key: 'overdue', label: '已逾期', value: todoCounts.value.overdue || 0, bucket: 'bucket-due' },
])
function scrollToBucket(id) {
  const el = document.getElementById(id)
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

// ── 待办五桶（待接单/待接手/待回复/待验收/到期；M3+X1 全量点亮） ──
const todos = ref({ pending_responses: [], pending_transfers: [], to_review: [], due: [], handoffs: [] })
const todosLoading = ref(false)
const todosFailed = ref(false)       // 失败与空态分开：干部不错过转交接手/待验收
async function loadTodos() {
  todosLoading.value = true
  todosFailed.value = false
  try {
    const res = await workService.fetchTodos()
    todos.value = {
      pending_responses: res.data?.pending_responses || [],
      pending_transfers: res.data?.pending_transfers || [],
      to_review: res.data?.to_review || [],
      due: res.data?.due || [],
      handoffs: res.data?.handoffs || [],        // X1 待接单（跨组交付）
    }
  } catch {
    todosFailed.value = true
  } finally {
    todosLoading.value = false
  }
}
const hasAnyTodo = computed(() =>
  todos.value.pending_responses.length || todos.value.pending_transfers.length
  || todos.value.to_review.length || todos.value.due.length || todos.value.handoffs.length)

// ── 最近活动（fetchItems 第一页 8 条，跨我的可见工作区） ──
const recentItems = ref([])
const recentLoading = ref(true)
const recentFailed = ref(false)
async function loadRecent() {
  recentLoading.value = true
  recentFailed.value = false
  try {
    const res = await workService.fetchItems({ page: 1, page_size: 8 })
    recentItems.value = res.data?.items || []
  } catch {
    recentFailed.value = true
  } finally {
    recentLoading.value = false
  }
}

// 转交决策按「转交 id + 动作」分键：多张卡互不齐转
const deciding = reactive({})
const decidingHandoff = ref(false)
async function decideHandoff(handoffId, action) {
  if (decidingHandoff.value) return
  let declined = false
  if (action === 'decline') {
    let reason = ''
    try {
      const r = await ElMessageBox.prompt('拒绝原因（必填）', '拒绝跨组交付',
        { confirmButtonText: '确认拒绝', cancelButtonText: '取消', inputPlaceholder: '如：本周发版窗口已满' })
      reason = (r?.value || '').trim()
    } catch {
      return                                   // 用户取消
    }
    if (!reason) {
      ElMessage.warning('拒绝原因必填')
      return
    }
    decidingHandoff.value = true
    try {
      const res = await workService.decideHandoff(handoffId, 'decline', { reason })
      ElMessage.success(res.message || '已拒绝')
      declined = true
    } catch (e) {
      ElMessage.error(e.response?.data?.message || '操作失败')
    } finally {
      decidingHandoff.value = false
    }
  } else {
    decidingHandoff.value = true
    try {
      const res = await workService.decideHandoff(handoffId, action)
      ElMessage.success(res.message || '已处理')
    } catch (e) {
      ElMessage.error(e.response?.data?.message || '操作失败')
    } finally {
      decidingHandoff.value = false
    }
  }
  if (declined || action === 'accept') {
    await Promise.allSettled([loadTodos(), refreshSummary()])
    if (action === 'accept') {
      ElMessage.info('任务已建到本组「小组事项」，可改派给组员')
    }
  }
}

async function decideTransfer(transferId, action) {
  const key = `${transferId}:${action}`
  if (deciding[key]) return
  deciding[key] = true
  try {
    const res = await workService.decideTransfer(transferId, action)
    ElMessage.success(res.message || '已处理')
    await Promise.allSettled([loadTodos(), refreshSummary()])
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '操作失败')
  } finally {
    delete deciding[key]
  }
}

onMounted(() => {
  loadTodos()
  loadRecent()
})
</script>

<template>
  <div class="work-overview">
    <!-- 第一排：数字块（点击跳对应桶/区） -->
    <div class="stat-row">
      <button v-for="b in statBlocks" :key="b.key" type="button"
              class="stat-block" :class="{ 'stat-block--hot': b.value > 0 }"
              @click="scrollToBucket(b.bucket)">
        <span class="stat-value ws-num">{{ b.value }}</span>
        <span class="stat-label">{{ b.label }}</span>
      </button>
    </div>

    <!-- 行动桶区（骨架 → 失败重试 → 空态 → 分桶列表） -->
    <DewSkeleton v-if="todosLoading && !hasAnyTodo" variant="text" :lines="3" class="todo-sk" />
    <DewCard v-else-if="todosFailed" size="md" variant="flat">
      <p class="state-text">待办加载失败，转交接手与待验收可能被错过，请重试</p>
      <DewButton size="sm" :loading="todosLoading" @click="loadTodos">重试</DewButton>
    </DewCard>
    <DewCard v-else-if="!hasAnyTodo" size="md" variant="flat">
      <p class="state-text">当前没有等待你行动的事项；待回复、待接手、待验收与到期任务会出现在这里</p>
    </DewCard>
    <template v-else>
      <!-- 待接单：跨组交付（仅协调员出现此桶） -->
      <div v-if="todos.handoffs.length" id="bucket-handoffs" class="bucket-title">待接单</div>
      <DewCard v-for="h in todos.handoffs" :key="h.id" size="md" variant="flat" class="todo-card">
        <div class="todo-row">
          <div class="todo-main">
            <div class="todo-title">[{{ h.kind }}] {{ h.item_title }}</div>
            <div class="todo-meta">
              <span>{{ h.from_group_name }} 交付给本组</span>
              <span class="todo-due" v-if="h.deadline">期望 {{ h.deadline }} 前</span>
            </div>
          </div>
          <DewButton size="sm" type="danger" plain :loading="decidingHandoff"
                     @click="decideHandoff(h.id, 'decline')">拒绝</DewButton>
          <DewButton size="sm" active :loading="decidingHandoff"
                     @click="decideHandoff(h.id, 'accept')">接单</DewButton>
        </div>
      </DewCard>
      <!-- 待接手：转交确认 -->
      <div v-if="todos.pending_transfers.length" id="bucket-transfers" class="bucket-title">待接手</div>
      <DewCard v-for="t in todos.pending_transfers" :key="t.transfer_id" size="md" variant="flat" class="todo-card">
        <div class="todo-row">
          <div class="todo-main todo-main--link" @click="router.push(`/work/items/${t.item_id}`)">
            <div class="todo-title">{{ t.item_title }}</div>
            <div class="todo-meta">
              <span>转交给你的任务，确认后你成为负责人</span>
              <span class="todo-due">确认期限 {{ t.expires_at }}</span>
            </div>
          </div>
          <DewButton size="sm" type="danger"
                     :loading="!!deciding[`${t.transfer_id}:reject`]"
                     @click="decideTransfer(t.transfer_id, 'reject')">拒绝</DewButton>
          <DewButton size="sm" active
                     :loading="!!deciding[`${t.transfer_id}:accept`]"
                     @click="decideTransfer(t.transfer_id, 'accept')">接手</DewButton>
        </div>
      </DewCard>
      <!-- 待回复 -->
      <div v-if="todos.pending_responses.length" id="bucket-responses" class="bucket-title">待回复</div>
      <DewCard v-for="t in todos.pending_responses" :key="t.request_id" size="md" variant="flat" class="todo-card">
        <div class="todo-row">
          <div class="todo-main todo-main--link" @click="router.push(`/work/items/${t.item_id}`)">
            <div class="todo-title">{{ t.item_title }}</div>
            <div class="todo-meta">
              <span>{{ t.requested_by }} 请求你回复</span>
              <span v-if="t.due_at" class="todo-due">建议时限 {{ t.due_at }}</span>
              <span>{{ t.created_at }}</span>
            </div>
          </div>
          <DewButton size="sm">去回复</DewButton>
        </div>
      </DewCard>
      <!-- 待验收 -->
      <div v-if="todos.to_review.length" id="bucket-review" class="bucket-title">待验收</div>
      <DewCard v-for="t in todos.to_review" :key="t.item_id" size="md" variant="flat" class="todo-card">
        <div class="todo-row">
          <div class="todo-main todo-main--link" @click="router.push(`/work/items/${t.item_id}`)">
            <div class="todo-title">{{ t.item_title }}</div>
            <div class="todo-meta"><span>提交待你验收</span></div>
          </div>
          <DewButton size="sm">去验收</DewButton>
        </div>
      </DewCard>
    </template>

    <!-- 双列信息区：左 即将到期（逾期红显）｜右 最近活动 -->
    <div class="info-grid">
      <DewCard id="bucket-due" size="md" variant="flat" class="info-card">
        <div class="info-head">
          <span class="info-title">即将到期</span>
          <router-link class="info-more" to="/work/records">全部记录</router-link>
        </div>
        <DewSkeleton v-if="todosLoading && !todos.due.length" variant="text" :lines="3" />
        <p v-else-if="!todos.due.length" class="info-empty">暂无到期任务</p>
        <div v-for="t in todos.due.slice(0, 8)" :key="t.item_id"
             class="info-row todo-main--link" @click="router.push(`/work/items/${t.item_id}`)">
          <span class="info-name">{{ t.item_title }}</span>
          <span class="info-sub ws-num" :class="{ 'info-due--hot': t.overdue }">
            截止 {{ t.due_at }}{{ t.overdue ? '（已逾期）' : '' }}
          </span>
        </div>
      </DewCard>

      <DewCard size="md" variant="flat" class="info-card">
        <div class="info-head">
          <span class="info-title">最近活动</span>
          <router-link class="info-more" to="/work/items">小组事项</router-link>
        </div>
        <DewSkeleton v-if="recentLoading && !recentItems.length" variant="text" :lines="3" />
        <p v-else-if="recentFailed" class="info-empty">最近活动加载失败</p>
        <p v-else-if="!recentItems.length" class="info-empty">暂无事项动态</p>
        <div v-for="it in recentItems" :key="it.id"
             class="info-row todo-main--link" @click="router.push(`/work/items/${it.id}`)">
          <span class="info-name">
            <span v-if="it.unread" class="unread-dot" />{{ it.title }}
          </span>
          <span class="info-sub">{{ it.group_name }} · {{ it.last_activity_at }}</span>
        </div>
      </DewCard>
    </div>
  </div>
</template>

<style scoped>
/* ── 数字块 ── */
.stat-row { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 18px; }
.stat-block {
  flex: 1; min-width: 120px;
  display: flex; flex-direction: column; align-items: center; gap: 2px;
  padding: 14px 12px; border-radius: 10px;
  border: 1px solid var(--ws-border);
  background: var(--ws-panel);
  font-family: inherit; cursor: pointer;
  transition: border-color 0.2s ease, transform 0.2s ease;
}
.stat-block:hover { border-color: var(--ws-border-strong); transform: translateY(-1px); }
.stat-value { font-size: 24px; font-weight: 700; color: var(--dew-text-heading); }
.stat-block--hot .stat-value { color: var(--el-color-danger, #f56c6c); }
.stat-label { font-size: 12.5px; color: var(--dew-text-muted); }

.todo-sk { margin-bottom: 14px; }
.todo-card { margin-bottom: 10px; }
.todo-row { display: flex; align-items: center; gap: 12px; }
.todo-main { flex: 1; min-width: 0; }
.todo-main--link { cursor: pointer; border-radius: 6px; }
.todo-title { font-size: 14.5px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.todo-meta { display: flex; gap: 10px; margin-top: 4px; font-size: 12px; color: var(--dew-text-muted); flex-wrap: wrap; }
.todo-due { color: var(--el-color-warning, #e6a23c); }
.bucket-title {
  font-size: 13px; font-weight: 600; color: var(--dew-text-muted);
  margin: 6px 0 8px; scroll-margin-top: 64px;
}
.state-text { margin: 0 0 12px; font-size: 13px; color: var(--dew-text-muted); }

/* ── 双列信息区（对称等宽：两侧行结构同构，标题超长各自省略） ── */
.info-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 14px;
  margin-top: 18px; align-items: start;
}
.info-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.info-title { font-size: 14px; font-weight: 600; }
.info-more { font-size: 12px; color: var(--dew-text-muted); text-decoration: none; }
.info-more:hover { color: var(--color-primary); }
.info-row {
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
  padding: 7px 4px; border-bottom: 1px dashed var(--ws-border);
}
.info-row:last-child { border-bottom: none; }
.info-name {
  flex: 1; min-width: 0; display: inline-flex; align-items: center; gap: 6px;
  font-size: 13px; font-weight: 500;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.unread-dot {
  width: 7px; height: 7px; border-radius: 50%; flex: none;
  background: var(--el-color-danger, #f56c6c);
}
.info-sub { flex: none; font-size: 12px; color: var(--dew-text-muted); }
.info-due--hot { color: var(--el-color-danger, #f56c6c); font-weight: 600; }
.info-empty { margin: 4px 0; font-size: 12.5px; color: var(--dew-text-muted); }

@media (max-width: 768px) {
  .info-grid { grid-template-columns: 1fr; }
  .stat-block { min-width: 96px; }
}
</style>
