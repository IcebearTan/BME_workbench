<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { DewDialog, DewInput, DewButton } from '@bme/dew-ui'
import { workService, VISIBILITY_LABELS } from '../../services/workService'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  workspaces: { type: Array, default: () => [] },
  defaultWorkspaceId: { type: Number, default: null },
})
const emit = defineEmits(['update:modelValue', 'created'])
const router = useRouter()
const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})
const form = reactive({ workspaceId: null, kind: 'topic', title: '', body: '', visibility: 'workspace' })
const saving = ref(false)
const visibilityExpanded = ref(false)
// 在同一次打开中复用幂等键；创建超时后重试仍返回同一份草稿。
const idempotencyKey = ref('')

watch(visible, (open) => {
  if (!open) return
  Object.assign(form, {
    workspaceId: props.defaultWorkspaceId || props.workspaces[0]?.id || null,
    kind: 'topic', title: '', body: '', visibility: 'workspace',
  })
  visibilityExpanded.value = false
  idempotencyKey.value = `create-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}, { immediate: true })

const canSubmit = computed(() => Boolean(form.workspaceId && form.title.trim() && form.title.trim().length <= 200))

function errorMessage(error, fallback) {
  return error.response?.data?.message || error.response?.data?.error?.message || fallback
}

async function submit(publishNow = false) {
  if (!canSubmit.value || saving.value) return
  saving.value = true
  let created
  try {
    const res = await workService.createItem({
      workspace_id: form.workspaceId,
      kind: form.kind,
      title: form.title.trim(),
      visibility: form.visibility,
      body: form.body.trim() || null,
      idempotency_key: idempotencyKey.value,
    })
    created = res.data
    if (!created?.id) throw new Error('missing item')
  } catch (error) {
    ElMessage.error(errorMessage(error, '创建失败，请重试'))
    saving.value = false
    return
  }

  // 任务先进入详情补充执行安排；话题发布失败时保留已创建的草稿。
  if (publishNow && form.kind === 'topic' && created.status === 'draft') {
    try {
      if (!Number.isInteger(created.version)) {
        const current = await workService.fetchItem(created.id)
        if (current.data?.id !== created.id || !Number.isInteger(current.data.version)) throw new Error('missing version')
        created = current.data
      }
      if (!Number.isInteger(created?.version)) throw new Error('missing version')
      if (created.status === 'draft') {
        await workService.runCommand(created.id, { command: 'publish', expected_version: created.version })
      }
    } catch (error) {
      ElMessage.warning(`草稿已保存，但发布失败：${errorMessage(error, '请在详情页重试发布')}`)
      finishCreate(created.id)
      return
    }
  }
  ElMessage.success(form.kind === 'task'
    ? '任务已创建，可在事项设置中补充负责人和截止时间'
    : (publishNow ? '话题已发布' : '草稿已保存'))
  finishCreate(created.id)
}

function finishCreate(itemId) {
  visible.value = false
  emit('created', itemId)
  router.push(`/work/items/${itemId}`)
  saving.value = false
}
</script>

<template>
  <DewDialog v-model="visible" title="发起工作事项" :width="560"
             :close-on-click-modal="!saving" :close-on-press-escape="!saving" :show-close="!saving">
    <el-form label-width="76px" :disabled="saving">
      <el-form-item label="类型">
        <el-radio-group v-model="form.kind">
          <el-radio-button value="topic">话题</el-radio-button>
          <el-radio-button value="task">任务</el-radio-button>
        </el-radio-group>
        <div class="hint-text">
          {{ form.kind === 'topic' ? '先发起讨论，需要执行时再转为任务。' : '先记下这件事，创建后再安排负责人和截止时间。' }}
        </div>
      </el-form-item>
      <el-form-item label="工作区" required>
        <el-select v-model="form.workspaceId" style="width: 100%" placeholder="选择组工作区"
                   :disabled="workspaces.length <= 1">
          <el-option v-for="workspace in workspaces" :key="workspace.id"
                     :label="workspace.group_name" :value="workspace.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="标题" required>
        <DewInput v-model="form.title" maxlength="200" show-word-limit :disabled="saving"
                  placeholder="一句话说清这件事是什么" />
        <div v-if="form.title.trim().length > 200" class="hint-text">标题最多 200 字</div>
      </el-form-item>
      <el-form-item label="简短说明">
        <el-input v-model="form.body" type="textarea" :rows="3" maxlength="2000" show-word-limit
                  placeholder="补充背景或希望得到的帮助（选填）" />
      </el-form-item>
      <div class="visibility-note">
        <template v-if="form.kind === 'topic'">
          <span>{{ form.visibility === 'workspace' ? '发布后本组成员可见。' : '发布后仅你和被邀请的参与人可见。' }}</span>
          <DewButton type="ghost" size="sm" :disabled="saving" @click="visibilityExpanded = !visibilityExpanded">
            {{ visibilityExpanded ? '收起' : '调整可见范围' }}
          </DewButton>
        </template>
        <span v-else>创建后为仅自己可见的草稿。发布前可在事项设置中调整可见范围。</span>
      </div>
      <el-form-item v-if="form.kind === 'topic' && visibilityExpanded" label="发布可见">
        <el-radio-group v-model="form.visibility">
          <el-radio v-for="(label, key) in VISIBILITY_LABELS" :key="key" :value="key">{{ label }}</el-radio>
        </el-radio-group>
      </el-form-item>
    </el-form>
    <template #footer>
      <DewButton :disabled="saving" @click="visible = false">取消</DewButton>
      <DewButton v-if="form.kind === 'topic'" :disabled="!canSubmit || saving" @click="submit(false)">保存草稿</DewButton>
      <DewButton active :loading="saving" :disabled="!canSubmit" @click="submit(form.kind === 'topic')">
        {{ form.kind === 'task' ? '创建任务' : '发布话题' }}
      </DewButton>
    </template>
  </DewDialog>
</template>

<style scoped>
.hint-text, .visibility-note { font-size: 12px; color: var(--dew-text-muted); line-height: 1.6; }
.hint-text { width: 100%; margin-top: 4px; }
.visibility-note { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin: 0 0 10px 76px; }
@media (max-width: 600px) {
  .visibility-note { margin-left: 0; }
}
</style>
