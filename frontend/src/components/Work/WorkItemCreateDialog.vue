<script setup>
// 新建话题/任务对话框（M3）：任务必填负责人+截止（发布前校验）；负责人选择源
// 为 /work/candidates（仅显示有协作资格者）。创建即草稿，「立即发布」时紧接着
// 执行 publish 命令并跳转详情。
import { ref, reactive, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useStore } from 'vuex'
import { ElMessage } from 'element-plus'
import { MdEditor } from 'md-editor-v3'
import 'md-editor-v3/lib/style.css'
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
  set: (v) => emit('update:modelValue', v),
})

const form = reactive({
  workspaceId: null, kind: 'topic', title: '', visibility: 'workspace', body: '',
  publishNow: true,
  assigneeId: null, dueAt: null, priority: 'normal',
  acceptCriteria: '', reviewerId: null,
})
const saving = ref(false)
const candidates = ref([])
const candidatesLoading = ref(false)
// 幂等键在对话框打开时生成一次、整个生命周期复用：创建超时重试不会另建重复草稿
const idempotencyKey = ref('')

const PRIORITY_OPTIONS = [
  { value: 'normal', label: '普通' }, { value: 'high', label: '高' }, { value: 'urgent', label: '紧急' },
]

// 正文编辑器工具栏：保留基础排版与列表/引用/代码/链接/表格；排除重工具与图片
// （弹窗内空间有限；图片走附件面板，无图床通道）
const TOOLBAR_EXCLUDE = [
  'mermaid', 'katex', 'github', 'htmlPreview', 'save', 'sub', 'sup',
  'catalog', 'fullscreen', 'image', 'pdf', 'prettier', 'strike', 'preview',
]
const store = useStore()
const isDarkMode = computed(() => store.getters.isDarkMode)

async function loadCandidates() {
  if (candidates.value.length) return
  candidatesLoading.value = true
  try {
    const res = await workService.fetchCandidates()
    candidates.value = res.data?.candidates || []
  } catch { candidates.value = [] }
  finally { candidatesLoading.value = false }
}

watch(visible, (open) => {
  if (open) {
    form.workspaceId = props.defaultWorkspaceId || props.workspaces[0]?.id || null
    form.kind = 'topic'
    form.title = ''
    form.visibility = 'workspace'
    form.body = ''
    form.publishNow = true
    form.assigneeId = null
    form.dueAt = null
    form.priority = 'normal'
    form.acceptCriteria = ''
    form.reviewerId = null
    idempotencyKey.value = `create-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
  }
})
watch(() => form.kind, (k) => { if (k === 'task') loadCandidates() })

const canSubmit = computed(() => {
  if (!form.workspaceId || form.title.trim().length < 2) return false
  if (form.kind === 'task' && (!form.assigneeId || !form.dueAt)) return false
  return true
})

async function submit() {
  if (!canSubmit.value || saving.value) return
  saving.value = true
  // 第一步：创建草稿（幂等键复用，重试同键不重复建）
  let itemId = null
  try {
    const payload = {
      workspace_id: form.workspaceId,
      kind: form.kind,
      title: form.title.trim(),
      visibility: form.visibility,
      body: form.body.trim() || null,
      idempotency_key: idempotencyKey.value,
    }
    if (form.kind === 'task') {
      payload.task = {
        assignee_user_id: form.assigneeId,
        due_at: form.dueAt,
        priority: form.priority,
      }
      if (form.acceptCriteria.trim()) payload.task.accept_criteria = form.acceptCriteria.trim()
      if (form.reviewerId) payload.task.reviewer_user_id = form.reviewerId
    }
    const res = await workService.createItem(payload)
    itemId = res.data?.id || null
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '创建失败，请重试')
    saving.value = false
    return
  }
  // 第二步：立即发布（失败不再报「创建失败」——草稿已建，进详情可重发）
  if (form.publishNow && itemId) {
    try {
      await workService.runCommand(itemId, { command: 'publish', expected_version: 1 })
    } catch (e) {
      ElMessage.warning(e.response?.data?.message
        ? `草稿已保存，但发布失败：${e.response.data.message}`
        : '草稿已保存，但发布失败；可在详情页重试发布')
      finishCreate(itemId)
      return
    }
  }
  ElMessage.success(form.publishNow
    ? (form.kind === 'task' ? '任务已发布' : '话题已发布') : '草稿已保存')
  finishCreate(itemId)
}

function finishCreate(itemId) {
  visible.value = false
  emit('created', itemId)
  if (itemId) router.push(`/work/items/${itemId}`)
  saving.value = false
}
</script>

<template>
  <DewDialog v-model="visible" title="发起工作事项" :width="660">
    <el-form label-width="84px">
      <el-form-item label="类型">
        <el-radio-group v-model="form.kind">
          <el-radio-button value="topic">话题</el-radio-button>
          <el-radio-button value="task">任务</el-radio-button>
        </el-radio-group>
        <div class="hint-text">
          {{ form.kind === 'topic'
            ? '讨论形成结论后可转为任务（保留全部讨论）'
            : '需要执行与验收的工作；负责人唯一，转交须对方确认' }}
        </div>
      </el-form-item>
      <el-form-item label="工作区" required>
        <el-select v-model="form.workspaceId" style="width: 100%;" placeholder="选择组工作区"
                   :disabled="workspaces.length <= 1">
          <el-option v-for="w in workspaces" :key="w.id" :label="w.group_name" :value="w.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="标题" required>
        <DewInput v-model="form.title" maxlength="100" show-word-limit
                  placeholder="一句话说清这件事是什么" />
      </el-form-item>
      <el-form-item label="可见范围">
        <el-radio-group v-model="form.visibility">
          <el-radio v-for="(label, key) in VISIBILITY_LABELS" :key="key" :value="key">{{ label }}</el-radio>
        </el-radio-group>
        <div class="hint-text">
          {{ form.visibility === 'workspace'
            ? '本工作区已开通的成员都可以看到并参与'
            : '只有你和被邀请的参与人可以看到；协调员也没有天然阅读权' }}
        </div>
      </el-form-item>

      <template v-if="form.kind === 'task'">
        <el-form-item label="负责人" required>
          <el-select v-model="form.assigneeId" filterable style="width: 100%;"
                     :loading="candidatesLoading" placeholder="搜索并选择（仅显示有资格者）">
            <el-option v-for="c in candidates" :key="c.user_id" :label="c.username" :value="c.user_id">
              <span>{{ c.username }}</span>
              <span class="option-id">#{{ c.user_id }}</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="截止时间" required>
          <el-date-picker v-model="form.dueAt" type="date" value-format="YYYY-MM-DD"
                          placeholder="只选日期则截止当天 23:59" style="width: 220px;" />
        </el-form-item>
        <el-form-item label="优先级">
          <el-radio-group v-model="form.priority">
            <el-radio v-for="p in PRIORITY_OPTIONS" :key="p.value" :value="p.value">{{ p.label }}</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="验收标准">
          <el-input v-model="form.acceptCriteria" type="textarea" :rows="2" maxlength="2000"
                    placeholder="怎样算完成（选填，验收时对照）" />
        </el-form-item>
        <el-form-item label="验收人">
          <el-select v-model="form.reviewerId" filterable clearable style="width: 100%;"
                     :loading="candidatesLoading" placeholder="需要他人验收时选择（选填）">
            <el-option v-for="c in candidates" :key="c.user_id" :label="c.username" :value="c.user_id" />
          </el-select>
          <div class="hint-text">课程发布、正式资料等重要交付建议指定另一人验收</div>
        </el-form-item>
      </template>

      <el-form-item label="正文">
        <!-- L3-2：正文升级 md-editor（阅读端 MdPreview 早已按 md 渲染，编辑端此前
             是裸源码 textarea）。图片不入工具栏——工作台图片走附件面板，无社区图床 -->
        <MdEditor
          v-model="form.body"
          class="body-editor"
          :theme="isDarkMode ? 'dark' : 'light'"
          :toolbars-exclude="TOOLBAR_EXCLUDE"
          :no-prettier="true"
          :max-length="20000"
          :style="{ height: '240px' }"
          placeholder="补充说明、背景与要解决的问题。支持 Markdown，详情页按格式渲染"
        />
      </el-form-item>
      <el-form-item label="发布">
        <el-checkbox v-model="form.publishNow">立即发布（取消则保存为仅自己可见的草稿）</el-checkbox>
      </el-form-item>
    </el-form>
    <template #footer>
      <DewButton @click="visible = false">取消</DewButton>
      <DewButton active :loading="saving" :disabled="!canSubmit" @click="submit">
        {{ form.publishNow ? (form.kind === 'task' ? '发布任务' : '发布话题') : '保存草稿' }}
      </DewButton>
    </template>
  </DewDialog>
</template>

<style scoped>
.hint-text {
  width: 100%;
  font-size: 12px;
  color: var(--dew-text-muted);
  line-height: 1.6;
}
.option-id { float: right; color: var(--dew-text-muted); font-size: 12px; }
/* 正文 md-editor：撑满表单列；DewDialog 实色底上直接落编辑器自身配色 */
.body-editor {
  width: 100%;
  border-radius: 10px;
  overflow: hidden;
}
</style>
