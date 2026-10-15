<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { DewDialog, DewInput, DewButton } from '@bme/dew-ui'
import { workService, VISIBILITY_LABELS } from '../../services/workService'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  item: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'saved'])
const visible = computed({ get: () => props.modelValue, set: (value) => emit('update:modelValue', value) })
const form = reactive({ title: '', body: '', visibility: 'workspace', assignee: null, dueAt: null,
  priority: 'normal', reviewer: null, criteria: '' })
const openedItem = ref(null)
const initial = ref(null)
const saving = ref(false)
const conflict = ref(false)
const candidates = ref([])
const candidatesLoading = ref(false)
const candidatesFailed = ref(false)
const isTask = computed(() => openedItem.value?.kind === 'task')
const isDraft = computed(() => openedItem.value?.status === 'draft')
const canEditAcceptance = computed(() => !['review', 'done', 'cancelled'].includes(openedItem.value?.status))
const priorityOptions = [{ value: 'normal', label: '普通' }, { value: 'high', label: '高' }, { value: 'urgent', label: '紧急' }]

function fieldsOf(item) {
  return {
    title: item.title || '', body: item.body || '', visibility: item.visibility || 'workspace',
    assignee: item.task?.assignee_user_id || null,
    dueAt: item.task?.due_at?.replace(' ', 'T') || null,
    priority: item.task?.priority || 'normal', reviewer: item.task?.reviewer_user_id || null,
    criteria: item.task?.accept_criteria || '',
  }
}

async function loadCandidates() {
  candidatesLoading.value = true
  candidatesFailed.value = false
  try {
    const res = await workService.fetchCandidates()
    candidates.value = res.data?.candidates || []
  } catch {
    candidates.value = []
    candidatesFailed.value = true
  } finally {
    candidatesLoading.value = false
  }
}

watch(visible, (open) => {
  if (!open || !props.item) return
  // 在打开时捕获版本和字段；后台刷新不能覆盖仍在编辑的内容。
  openedItem.value = { id: props.item.id, version: props.item.version, kind: props.item.kind, status: props.item.status }
  initial.value = fieldsOf(props.item)
  Object.assign(form, initial.value)
  conflict.value = false
  if (isTask.value && (isDraft.value || canEditAcceptance.value)) loadCandidates()
}, { immediate: true })

const candidateOptions = computed(() => {
  const options = [...candidates.value]
  for (const [key, label] of [['assignee_user_id', 'assignee_name'], ['reviewer_user_id', 'reviewer_name']]) {
    const userId = props.item?.task?.[key]
    if (userId && !options.some(candidate => candidate.user_id === userId)) {
      options.push({ user_id: userId, username: props.item.task[label] || `#${userId}` })
    }
  }
  return options
})

const changedFields = computed(() => {
  if (!initial.value) return {}
  const payload = {}
  for (const key of ['title', 'body', 'visibility']) {
    const value = key === 'title' ? form.title.trim() : form[key]
    if (value !== initial.value[key]) payload[key] = value
  }
  if (isTask.value) {
    const task = {}
    const mapping = { priority: 'priority' }
    if (isDraft.value) Object.assign(mapping, { assignee: 'assignee_user_id', dueAt: 'due_at' })
    if (canEditAcceptance.value) Object.assign(mapping, { reviewer: 'reviewer_user_id', criteria: 'accept_criteria' })
    for (const [formKey, apiKey] of Object.entries(mapping)) {
      if (form[formKey] !== initial.value[formKey]) task[apiKey] = form[formKey] || null
    }
    if (Object.keys(task).length) payload.task = task
  }
  return payload
})
const canSave = computed(() => Boolean(form.title.trim() && form.title.trim().length <= 200 && Object.keys(changedFields.value).length && !conflict.value))

async function save() {
  if (!canSave.value || saving.value) return
  saving.value = true
  const itemId = openedItem.value.id
  try {
    await workService.patchItem(itemId, { expected_version: openedItem.value.version, ...changedFields.value })
    ElMessage.success('事项设置已保存')
    visible.value = false
    emit('saved', { id: itemId, conflict: false })
  } catch (error) {
    if (error.response?.status === 409) {
      conflict.value = true
      ElMessage.warning('事项已有更新，已保留你的输入并刷新详情')
      emit('saved', { id: itemId, conflict: true })
    } else {
      ElMessage.error(error.response?.data?.message || error.response?.data?.error?.message || '保存失败，请重试')
    }
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <DewDialog v-model="visible" title="事项设置" :width="640" :close-on-click-modal="false"
             :close-on-press-escape="!saving" :show-close="!saving">
    <p v-if="conflict" class="conflict-note" role="alert">
      事项已有更新，当前输入已保留。请先保留需要的文字，关闭设置核对最新详情，再重新打开编辑。
    </p>
    <el-form label-width="88px" :disabled="saving || conflict">
      <el-form-item label="标题" required>
        <DewInput v-model="form.title" maxlength="200" show-word-limit :disabled="saving || conflict" placeholder="事项标题" />
        <div v-if="form.title.trim().length > 200" class="hint-text">标题最多 200 字</div>
      </el-form-item>
      <el-form-item label="正文">
        <el-input v-model="form.body" type="textarea" :rows="5" maxlength="20000"
                  placeholder="补充完整说明，支持 Markdown" />
      </el-form-item>
      <el-form-item label="可见范围">
        <el-radio-group v-model="form.visibility">
          <el-radio v-for="(label, key) in VISIBILITY_LABELS" :key="key" :value="key">{{ label }}</el-radio>
        </el-radio-group>
        <div class="hint-text">
          {{ isDraft ? '草稿始终仅自己可见；此设置在发布后生效。' : '' }}
          {{ form.visibility === 'workspace' ? '本工作区已开通的成员可以看到并参与。' : '仅发起人和被邀请的参与人可见，其他组员和协调员没有天然阅读权。' }}
        </div>
      </el-form-item>
      <template v-if="isTask">
        <div class="section-title">执行安排</div>
        <p v-if="isDraft" class="section-hint">可以先保存，发布任务前再补齐负责人和截止时间。</p>
        <template v-if="isDraft">
          <el-form-item label="负责人">
            <el-select v-model="form.assignee" filterable clearable :loading="candidatesLoading"
                       placeholder="待分派" style="width: 100%">
              <el-option v-for="candidate in candidateOptions" :key="candidate.user_id"
                         :label="candidate.username" :value="candidate.user_id" />
            </el-select>
          </el-form-item>
          <el-form-item label="截止时间">
            <el-date-picker v-model="form.dueAt" type="datetime" value-format="YYYY-MM-DDTHH:mm"
                            format="YYYY-MM-DD HH:mm" placeholder="待设置" style="width: 100%" />
          </el-form-item>
        </template>
        <p v-else class="section-hint">负责人和截止时间请通过详情页的“改派负责人”、“转交”和“改期”操作修改，以保留转交确认和调整原因。</p>
        <el-form-item label="优先级">
          <el-radio-group v-model="form.priority">
            <el-radio v-for="option in priorityOptions" :key="option.value" :value="option.value">{{ option.label }}</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="验收人">
          <el-select v-model="form.reviewer" filterable clearable :loading="candidatesLoading"
                     :disabled="!canEditAcceptance" placeholder="不指定验收人" style="width: 100%">
            <el-option v-for="candidate in candidateOptions" :key="candidate.user_id"
                       :label="candidate.username" :value="candidate.user_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="验收标准">
          <el-input v-model="form.criteria" type="textarea" :rows="3" maxlength="2000"
                    :disabled="!canEditAcceptance" placeholder="怎样算完成（选填）" />
          <div v-if="!canEditAcceptance" class="hint-text">待验收、已完成和已取消的任务保留现有验收约定。</div>
        </el-form-item>
        <div v-if="candidatesFailed" class="candidate-error">
          <span>人员列表加载失败，已填写的内容仍保留。</span>
          <DewButton type="ghost" size="sm" :disabled="saving || conflict" @click="loadCandidates">重试加载</DewButton>
        </div>
      </template>
    </el-form>
    <template #footer>
      <DewButton :disabled="saving" @click="visible = false">{{ conflict ? '关闭设置' : '取消' }}</DewButton>
      <DewButton active :loading="saving" :disabled="!canSave" @click="save">保存设置</DewButton>
    </template>
  </DewDialog>
</template>

<style scoped>
.hint-text { width: 100%; font-size: 12px; line-height: 1.6; color: var(--dew-text-muted); }
.section-title { margin: 20px 0 8px; padding-top: 16px; border-top: 1px solid var(--el-border-color-lighter); font-weight: 600; }
.section-hint { margin: 0 0 16px; font-size: 12px; line-height: 1.6; color: var(--dew-text-muted); }
.conflict-note { padding: 10px 12px; border-radius: 8px; color: var(--el-color-warning-dark-2); background: var(--el-color-warning-light-9); line-height: 1.7; }
.candidate-error { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--dew-text-muted); }
</style>
