<script setup>
// 邀请参与者对话框（§5.2 独立共享能力）：候选来自 /work/candidates
// （后端只返回有协作资格者——无权者不在可发送列表，§5.3）。
import { ref, reactive, computed, watch, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { DewDialog, DewButton } from '@bme/dew-ui'
import { workService } from '../../services/workService'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  itemId: { type: Number, required: true },
  existing: { type: Array, default: () => [] },     // 已是参与者的 user_id 列表
})
const emit = defineEmits(['update:modelValue', 'invited'])

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const candidates = ref([])
const loadingCandidates = ref(false)
const form = reactive({ userIds: [], groupId: null, ptype: 'collaborator' })
const saving = ref(false)
const failures = ref([])
const loadFailed = ref(false)
let disposed = false
onBeforeUnmount(() => { disposed = true })
const groups = computed(() => [...new Map(candidates.value.flatMap(c => c.groups || [])
  .map(g => [g.id, g])).values()])
const filteredCandidates = computed(() => candidates.value.filter(c =>
  !props.existing.includes(c.user_id) && (!form.groupId || (c.groups || []).some(g => g.id === form.groupId))))

// 候选人统一走 workService（服务层唯一入口约定，不再直调 api）
async function loadCandidates() {
  loadingCandidates.value = true
  loadFailed.value = false
  try {
    const res = await workService.fetchCandidates()
    const inSet = new Set(props.existing)
    candidates.value = (res.data?.candidates || [])
      .filter(c => !inSet.has(c.user_id))
  } catch (e) {
    candidates.value = []
    loadFailed.value = true
    ElMessage.error(e.response?.data?.message || '候选人加载失败')
  } finally {
    loadingCandidates.value = false
  }
}

watch(visible, (open) => {
  if (open) {
    form.userIds = []
    form.groupId = null
    form.ptype = 'collaborator'
    failures.value = []
    loadCandidates()
  }
})

async function submit() {
  if (!form.userIds.length || saving.value) return
  saving.value = true
  const targetItemId = props.itemId
  const ptype = form.ptype
  failures.value = []
  const succeeded = []
  try {
    for (const userId of [...form.userIds]) {
      if (disposed || props.itemId !== targetItemId) break
      try {
        await workService.addParticipant(targetItemId, { user_id: userId, ptype })
        succeeded.push(userId)
      } catch (e) {
        failures.value.push({ userId, name: candidates.value.find(c => c.user_id === userId)?.username || `#${userId}`,
          message: e.response?.data?.message || '邀请失败，请重试' })
      }
    }
    if (disposed || props.itemId !== targetItemId) return
    form.userIds = form.userIds.filter(id => !succeeded.includes(id))
    candidates.value = candidates.value.filter(c => !succeeded.includes(c.user_id))
    if (succeeded.length) {
      ElMessage.success(`已邀请 ${succeeded.length} 位成员，对方会收到通知`)
      emit('invited')
    }
    if (!failures.value.length) visible.value = false
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <DewDialog v-model="visible" title="邀请成员一起协作" :width="540"
             :close-on-click-modal="!saving" :close-on-press-escape="!saving" :show-close="!saving">
    <p class="invite-note">可邀请其他组成员一起讨论、回复和共享附件。邀请只开放当前事项，不会将对方加入本组。</p>
    <p v-if="loadFailed" role="alert">成员加载失败。<DewButton size="sm" @click="loadCandidates">重试</DewButton></p>
    <el-form label-width="80px">
      <el-form-item label="按组筛选">
        <el-select v-model="form.groupId" clearable placeholder="全部小组" :disabled="saving">
          <el-option v-for="g in groups" :key="g.id" :label="g.name" :value="g.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="成员" required>
        <el-select v-model="form.userIds" multiple filterable style="width: 100%;" :disabled="saving"
                   :loading="loadingCandidates" placeholder="搜索姓名，可一次选择多人">
          <el-option v-for="c in filteredCandidates" :key="c.user_id" :label="c.username" :value="c.user_id">
            <span>{{ c.username }}</span>
            <span class="option-meta">
              {{ (c.groups || []).map(g => g.name).join(' / ') || c.group_name || '' }}
            </span>
          </el-option>
        </el-select>
      </el-form-item>
      <el-form-item label="参与方式">
        <el-radio-group v-model="form.ptype" :disabled="saving">
          <el-radio value="collaborator">协作者</el-radio>
          <el-radio value="observer">观察者</el-radio>
        </el-radio-group>
      </el-form-item>
    </el-form>
    <div v-if="failures.length" role="alert" class="invite-failures">
      <p>以下成员未加入，可处理后重试；已成功的成员不会重复邀请。</p>
      <p v-for="failure in failures" :key="failure.userId">{{ failure.name }}：{{ failure.message }}</p>
    </div>
    <template #footer>
      <DewButton :disabled="saving" @click="visible = false">关闭</DewButton>
      <DewButton active :loading="saving" :disabled="!form.userIds.length || loadFailed" @click="submit">邀请所选成员</DewButton>
    </template>
  </DewDialog>
</template>

<style scoped>
.option-meta { float: right; color: var(--dew-text-muted); font-size: 12px; }
.invite-note { margin: 0 0 18px; color: var(--dew-text-muted); line-height: 1.7; font-size: 13px; }
.invite-failures { font-size: 13px; color: var(--el-color-danger); }
</style>
