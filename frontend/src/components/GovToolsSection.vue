<template>
  <div>
    <!-- 需接管事项（D01） -->
    <DewCard no-hover class="table-card">
      <template #header>
        <div class="card-head">
          <span>需接管事项</span>
          <span class="card-head-hint">活跃任务的负责人已失去协作资格；接手由协调员改派或转交完成</span>
        </div>
      </template>
      <div v-if="takeoverError" class="state-message">
        需接管队列暂不可用
        <el-button type="primary" link @click="fetchTakeover">重试</el-button>
      </div>
      <template v-else>
        <el-table :data="takeoverRows" v-loading="takeoverLoading" style="width: 100%"
                  max-height="calc(100vh - 320px)">
          <el-table-column label="事项" width="110">
            <template #default="{ row }">
              <span>#{{ row.item_id }}</span>
              <el-button class="copy-id-btn" link size="small" title="复制事项 ID"
                         @click="copyItemId(row.item_id)">
                <el-icon><CopyDocument /></el-icon>
              </el-button>
            </template>
          </el-table-column>
          <el-table-column prop="title" label="标题" min-width="160" show-overflow-tooltip />
          <el-table-column label="所属工作区" min-width="110">
            <template #default="{ row }">{{ row.group_name || '—' }}</template>
          </el-table-column>
          <el-table-column label="原负责人" width="120">
            <template #default="{ row }">{{ row.assignee_name }}<span class="option-id">#{{ row.assignee_user_id }}</span></template>
          </el-table-column>
          <el-table-column label="状态" width="90">
            <template #default="{ row }">{{ ITEM_STATUS_LABELS[row.status] || row.status }}</template>
          </el-table-column>
        </el-table>
        <p v-if="!takeoverRows.length && !takeoverLoading" class="section-empty">当前没有需接管的事项</p>
      </template>
    </DewCard>

    <!-- 治理工具：交接清单 + 紧急介入 -->
    <DewCard no-hover class="table-card">
      <template #header>
        <div class="card-head"><span>治理工具</span></div>
      </template>
      <div class="gov-tools">
        <div class="gov-tool">
          <div class="gov-tool-label">交接清单（调组/卸任前生成）</div>
          <div class="gov-tool-row">
            <el-select v-model="handoverUserId" filterable placeholder="选择成员"
                       style="width: 200px;" :loading="usersLoading">
              <el-option v-for="u in users" :key="u.User_Id" :label="u.User_Name" :value="u.User_Id" />
            </el-select>
            <el-button :disabled="!handoverUserId" @click="openHandover">生成清单</el-button>
          </div>
        </div>
        <div class="gov-tool">
          <div class="gov-tool-label">紧急介入读取受限事项（理由必填并留痕）</div>
          <div class="gov-tool-row">
            <el-input-number v-model="emergencyForm.itemId" :min="1" controls-position="right"
                             placeholder="事项 ID" style="width: 130px;" />
            <el-input v-model="emergencyForm.reason" maxlength="200" placeholder="介入理由"
                      style="width: 260px;" />
            <el-button type="warning" plain :loading="emergencyLoading"
                       :disabled="!emergencyForm.itemId || !emergencyForm.reason.trim()"
                       @click="submitEmergency">介入</el-button>
          </div>
        </div>
      </div>
    </DewCard>

    <!-- 交接清单弹窗 -->
    <el-dialog v-model="handoverVisible" :title="`交接清单 - ${handoverData?.user?.username || ''}`" width="640px">
      <div v-loading="handoverLoading">
        <template v-if="handoverData">
          <el-descriptions :column="2" size="small" border>
            <el-descriptions-item label="未完成任务">{{ handoverData.counts.unfinished }}</el-descriptions-item>
            <el-descriptions-item label="待其验收">{{ handoverData.counts.to_review }}</el-descriptions-item>
            <el-descriptions-item label="待其回复">{{ handoverData.counts.pending_responses }}</el-descriptions-item>
            <el-descriptions-item label="待确认转交">{{ handoverData.counts.pending_transfers }}</el-descriptions-item>
          </el-descriptions>
          <el-collapse v-if="handoverDetails.length" class="handover-details">
            <el-collapse-item v-for="sec in handoverDetails" :key="sec.key" :name="sec.key">
              <template #title>{{ sec.label }}（{{ sec.rows.length }}）</template>
              <ul class="detail-list">
                <li v-for="(r, i) in sec.rows" :key="i">
                  <span class="detail-item-id">#{{ r.item_id }}</span>
                  <span class="detail-item-title">{{ r.title || '（事项已删除）' }}</span>
                  <span v-if="r.meta" class="detail-item-meta">{{ r.meta }}</span>
                </li>
              </ul>
            </el-collapse-item>
          </el-collapse>
          <el-table :data="handoverData.grants" size="small" style="width: 100%; margin-top: 12px;">
            <el-table-column prop="id" label="授权" width="70" />
            <el-table-column prop="role" label="岗位" width="100" />
            <el-table-column label="状态">
              <template #default="{ row }">
                <el-tag size="small" :type="row.effective ? 'success' : 'warning'">
                  {{ row.effective ? '有效' : (row.reason || '已失效') }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
          <p class="dialog-text">清单为只读汇总；接手操作在对应事项页完成（改派/转交需对方确认）。</p>
        </template>
      </div>
      <template #footer>
        <el-button @click="handoverVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 紧急介入详情弹窗（只读投影，介入行为已留痕） -->
    <el-dialog v-model="emergencyDetailVisible" title="紧急介入 - 事项详情（只读）" width="640px">
      <template v-if="emergencyDetail">
        <el-descriptions :column="2" size="small" border>
          <el-descriptions-item label="标题" :span="2">{{ emergencyDetail.title }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag size="small" :type="ITEM_STATUS_TYPE[emergencyDetail.status] || 'info'">
              {{ ITEM_STATUS_LABELS[emergencyDetail.status] || emergencyDetail.status }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="所属工作区">{{ emergencyDetail.group_name || '—' }}</el-descriptions-item>
          <el-descriptions-item label="创建人">{{ emergencyDetail.created_by_name || '—' }}</el-descriptions-item>
          <el-descriptions-item label="最近活动">{{ emergencyDetail.last_activity_at || '—' }}</el-descriptions-item>
          <template v-if="emergencyDetail.task">
            <el-descriptions-item label="负责人">{{ emergencyDetail.task.assignee_name || '未分配' }}</el-descriptions-item>
            <el-descriptions-item label="截止时间">{{ emergencyDetail.task.due_at || '不限' }}</el-descriptions-item>
          </template>
        </el-descriptions>
        <div class="detail-block">
          <div class="detail-block-label">正文摘要</div>
          <p class="detail-body">{{ emergencyBodyExcerpt }}</p>
        </div>
        <div v-if="recentSubmissions.length" class="detail-block">
          <div class="detail-block-label">最近提交记录</div>
          <ul class="detail-list">
            <li v-for="s in recentSubmissions" :key="s.id">
              <span class="detail-item-id">#{{ s.seq }}</span>
              <span class="detail-item-title">{{ s.submitted_by_name || `用户 ${s.submitted_by}` }}</span>
              <span class="detail-item-meta">{{ s.created_at }}{{ s.decision ? ' · ' + DECISION_LABELS[s.decision] : ' · 待验收' }}</span>
            </li>
          </ul>
        </div>
        <p class="dialog-text">本次介入已留痕（理由：{{ emergencyReason }}）；此处为只读投影，不改变事项状态。</p>
      </template>
      <template #footer>
        <el-button @click="emergencyDetailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { CopyDocument } from '@element-plus/icons-vue'
import { DewCard } from '@bme/dew-ui'
import api from '../api'

// 与用户端 workService 的文案同源（事项状态/提交决议）
const ITEM_STATUS_LABELS = {
  draft: '草稿', open: '进行中', closed: '已关闭', todo: '待执行',
  in_progress: '进行中', blocked: '受阻', review: '待验收',
  done: '已完成', cancelled: '已取消',
}
const ITEM_STATUS_TYPE = {
  draft: 'info', open: 'primary', closed: 'info', todo: 'warning',
  in_progress: 'primary', blocked: 'danger', review: 'warning',
  done: 'success', cancelled: 'info',
}
const DECISION_LABELS = { accepted: '已通过', returned: '已退回' }

defineProps({
  /** 成员名单（交接清单选择用，主页面统一拉取） */
  users: { type: Array, default: () => [] },
  usersLoading: { type: Boolean, default: false },
})

// ── 需接管队列（D01：活跃任务负责人已失资格） ──
const takeoverRows = ref([])
const takeoverLoading = ref(false)
const takeoverError = ref(false)

const fetchTakeover = async () => {
  takeoverLoading.value = true
  takeoverError.value = false
  try {
    const res = await api({ url: '/work/governance/takeover-queue', method: 'get' })
    takeoverRows.value = res.data?.data?.items || []
  } catch {
    takeoverRows.value = []
    takeoverError.value = true
  } finally {
    takeoverLoading.value = false
  }
}

const copyItemId = async (itemId) => {
  const text = String(itemId)
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text)
    } else {
      const el = document.createElement('textarea')
      el.value = text
      el.style.cssText = 'position:fixed;top:-9999px;left:-9999px;opacity:0'
      document.body.appendChild(el)
      el.focus()
      el.select()
      const ok = document.execCommand('copy')
      document.body.removeChild(el)
      if (!ok) throw new Error('execCommand failed')
    }
    ElMessage.success(`已复制事项 ID ${text}`)
  } catch {
    ElMessage.warning(`复制失败，请手动记录事项 ID ${text}`)
  }
}

// ── 交接清单（§5.4：按成员汇总，计数 + 明细） ──
const handoverVisible = ref(false)
const handoverUserId = ref(null)
const handoverLoading = ref(false)
const handoverData = ref(null)

// 后端已回的明细数组整理为可折叠分组（无条目的分组不渲染）
const handoverDetails = computed(() => {
  const d = handoverData.value
  if (!d) return []
  const taskRow = (r) => ({
    item_id: r.item_id, title: r.title,
    meta: [r.role === 'reviewer' ? '验收人' : '负责人',
           ITEM_STATUS_LABELS[r.status] || r.status,
           r.due_at ? `截止 ${r.due_at}` : ''].filter(Boolean).join(' · '),
  })
  const sections = [
    { key: 'unfinished', label: '未完成任务明细', rows: (d.unfinished_tasks || []).map(taskRow) },
    { key: 'to_review', label: '待其验收明细', rows: (d.to_review || []).map(taskRow) },
    { key: 'responses', label: '待其回复明细', rows: (d.pending_responses || []).map((r) => ({
      item_id: r.item_id, title: r.title,
      meta: r.due_at ? `回复截止 ${r.due_at}` : '',
    })) },
    { key: 'transfers', label: '待确认转交明细', rows: (d.pending_transfers || []).map((r) => ({
      item_id: r.item_id, title: r.title,
      meta: r.expires_at ? `过期时间 ${r.expires_at}` : '',
    })) },
  ]
  return sections.filter((s) => s.rows.length)
})

const openHandover = async () => {
  handoverVisible.value = true
  handoverData.value = null
  if (handoverUserId.value) await loadHandover()
}

const loadHandover = async () => {
  if (!handoverUserId.value) return
  handoverLoading.value = true
  try {
    const res = await api({ url: '/work/governance/handover', method: 'get',
                            params: { user_id: handoverUserId.value } })
    handoverData.value = res.data?.data || null
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '交接清单加载失败')
  } finally {
    handoverLoading.value = false
  }
}

// ── 紧急介入（§5.4：理由必填 + 留痕；成功后展示只读详情） ──
const emergencyForm = reactive({ itemId: null, reason: '' })
const emergencyLoading = ref(false)
const emergencyDetailVisible = ref(false)
const emergencyDetail = ref(null)
const emergencyReason = ref('')

const emergencyBodyExcerpt = computed(() => {
  const body = String(emergencyDetail.value?.body || '')
    .replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()
  if (!body) return '（无正文）'
  return body.length > 160 ? `${body.slice(0, 160)}…` : body
})

const recentSubmissions = computed(() =>
  (emergencyDetail.value?.task?.submissions || []).slice(0, 3))

const submitEmergency = async () => {
  if (!emergencyForm.itemId || !emergencyForm.reason.trim() || emergencyLoading.value) return
  emergencyLoading.value = true
  try {
    const res = await api({ url: '/work/governance/emergency-access', method: 'post',
                            data: { item_id: emergencyForm.itemId,
                                    reason: emergencyForm.reason.trim() } })
    ElMessage.success(res.data?.message || '已介入并留痕')
    emergencyDetail.value = res.data?.data || null
    emergencyReason.value = emergencyForm.reason.trim()
    emergencyDetailVisible.value = Boolean(emergencyDetail.value)
    emergencyForm.itemId = null
    emergencyForm.reason = ''
    await fetchTakeover()
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '介入失败（检查事项 ID 与理由）')
  } finally {
    emergencyLoading.value = false
  }
}

defineExpose({ fetchTakeover })
</script>

<style scoped>
.table-card { margin-bottom: 16px; }
.table-card :deep(.dew-card__body) { padding: 16px; }

.card-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.card-head-hint { font-size: 12px; color: var(--el-text-color-secondary); font-weight: 400; }

.state-message { padding: 24px; text-align: center; color: var(--el-text-color-secondary); }

.copy-id-btn { margin-left: 4px; padding: 2px; vertical-align: middle; }

.option-id { margin-left: 6px; color: var(--el-text-color-secondary); font-size: 12px; }

.gov-tools { display: flex; flex-direction: column; gap: 14px; }
.gov-tool-label { font-size: 13px; font-weight: 600; margin-bottom: 6px; }
.gov-tool-row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }

.section-empty { margin: 8px 0 0; font-size: 12.5px; color: var(--el-text-color-secondary); }

.dialog-text { margin: 12px 0 0; font-size: 13px; color: var(--el-text-color-regular); line-height: 1.6; }

.handover-details { margin-top: 12px; }

.detail-list { margin: 0; padding: 0; list-style: none; }
.detail-list li { display: flex; align-items: baseline; gap: 8px; padding: 5px 0; font-size: 13px; }
.detail-list li + li { border-top: 1px dashed var(--el-border-color-lighter); }
.detail-item-id { color: var(--el-text-color-secondary); font-size: 12px; flex-shrink: 0; }
.detail-item-title { color: var(--el-text-color-primary); }
.detail-item-meta { color: var(--el-text-color-secondary); font-size: 12px; margin-left: auto; text-align: right; }

.detail-block { margin-top: 12px; }
.detail-block-label { font-size: 13px; font-weight: 600; margin-bottom: 6px; }
.detail-body { margin: 0; font-size: 13px; color: var(--el-text-color-regular); line-height: 1.7; }
</style>
