<script setup>
// 任务属性面板（M3）：负责人/验收人/时间/优先级/验收标准 + 提交历史。
// 提交不可覆盖、验收绑定具体提交（§8.2）；逾期是计算值高亮显示。
import { computed } from 'vue'
import { DewCard, DewTag } from '@bme/dew-ui'
import { Clock } from '@element-plus/icons-vue'

const props = defineProps({
  detail: { type: Object, required: true },
})

const task = computed(() => props.detail.task || null)
const PRIORITY_LABELS = { normal: '普通', high: '高', urgent: '紧急' }
const PRIORITY_TYPE = { normal: 'neutral', high: 'warning', urgent: 'danger' }
const DECISION_LABELS = { accepted: '已通过', returned: '已退回' }

const infoRows = computed(() => {
  if (!task.value) return []
  const rows = [
    { label: '负责人', value: task.value.assignee_name || `#${task.value.assignee_user_id || '待分派'}` },
    { label: '截止时间', value: task.value.due_at, danger: task.value.overdue,
      suffix: task.value.overdue ? '（已逾期）' : '' },
  ]
  if (task.value.start_at) rows.splice(1, 0, { label: '开始时间', value: task.value.start_at })
  if (task.value.reviewer_user_id) {
    rows.push({ label: '验收人', value: task.value.reviewer_name || `#${task.value.reviewer_user_id}` })
  }
  if (task.value.accept_criteria) rows.push({ label: '验收标准', value: task.value.accept_criteria })
  return rows
})
</script>

<template>
  <DewCard v-if="task" size="md" variant="flat" class="task-panel">
    <div class="panel-head">
      <el-icon :size="15"><Clock /></el-icon>
      <span class="panel-title">任务</span>
      <DewTag :type="PRIORITY_TYPE[task.priority] || 'neutral'" size="sm" round>
        {{ PRIORITY_LABELS[task.priority] || task.priority }}
      </DewTag>
    </div>
    <div class="info-grid">
      <div v-for="row in infoRows" :key="row.label" class="info-row">
        <span class="info-label">{{ row.label }}</span>
        <span class="info-value" :class="{ 'info-value--danger': row.danger }">
          {{ row.value }}{{ row.suffix || '' }}
        </span>
      </div>
    </div>

    <!-- 提交历史：每次提交不可覆盖，验收绑定具体提交 -->
    <div v-if="task.submissions?.length" class="submissions">
      <div class="sub-title">提交历史</div>
      <div v-for="sub in task.submissions" :key="sub.id" class="sub-row">
        <div class="sub-head">
          <span class="sub-seq">#{{ sub.seq }}</span>
          <span class="sub-by">{{ sub.submitted_by_name }}</span>
          <span class="sub-time">{{ sub.created_at }}</span>
          <DewTag v-if="sub.decision" :type="sub.decision === 'accepted' ? 'success' : 'danger'"
                  size="sm" round>{{ DECISION_LABELS[sub.decision] }}</DewTag>
          <DewTag v-else type="info" size="sm" round>待验收</DewTag>
        </div>
        <p v-if="sub.result_note" class="sub-note">{{ sub.result_note }}</p>
        <p v-if="sub.decision_note" class="sub-note sub-note--decision">
          验收意见：{{ sub.decision_note }}（{{ sub.decided_at }}）
        </p>
      </div>
    </div>
  </DewCard>
</template>

<style scoped>
.task-panel { margin-top: 14px; }
.panel-head { display: flex; align-items: center; gap: 6px; margin-bottom: 10px; }
.panel-title { font-size: 14px; font-weight: 600; margin-right: 4px; }

.info-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 8px 20px; }
.info-row { display: flex; gap: 8px; font-size: 13px; line-height: 1.7; }
.info-label { color: var(--dew-text-muted); flex: none; }
.info-value { word-break: break-all; }
.info-value--danger { color: var(--el-color-danger, #f56c6c); font-weight: 600; }

.submissions { margin-top: 14px; border-top: 1px dashed var(--el-border-color-lighter); padding-top: 10px; }
.sub-title { font-size: 13px; font-weight: 600; margin-bottom: 8px; }
.sub-row { padding: 8px 0; border-bottom: 1px dashed var(--el-border-color-lighter); }
.sub-row:last-child { border-bottom: none; }
.sub-head { display: flex; align-items: center; gap: 8px; font-size: 12.5px; }
.sub-seq { font-weight: 600; color: var(--dew-text-muted); }
.sub-by { font-weight: 600; }
.sub-time { color: var(--dew-text-muted); }
.sub-note { margin: 6px 0 0; font-size: 13px; line-height: 1.7; white-space: pre-wrap; }
.sub-note--decision { color: var(--dew-text-muted); }

@media (max-width: 768px) {
  .info-grid { grid-template-columns: 1fr; }
}
</style>
