<script setup>
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { DewCard, DewButton, DewTag } from '@bme/dew-ui'
import { workService } from '../../services/workService'

const props = defineProps({ item: { type: Object, required: true } })
const emit = defineEmits(['invite', 'handoff', 'promote', 'changed'])
const router = useRouter()
const records = ref({ outgoing: [], incoming: [] })
const loading = ref(false)
const failed = ref(false)
const busy = ref(false)
const downloading = ref(null)
const allowed = computed(() => props.item.allowed_actions || [])
const participants = computed(() => (props.item.participants || []).filter(p => p.user_id !== props.item.created_by))
const statusLabels = { offered: '待对方接单', accepted: '对方执行中', done: '已交付', declined: '已拒绝', withdrawn: '已撤回', expired: '已过期' }
let requestNumber = 0
async function refresh() {
  const current = ++requestNumber
  loading.value = true
  failed.value = false
  try {
    const res = await workService.fetchHandoffs(props.item.id)
    if (current === requestNumber) records.value = { outgoing: res.data?.outgoing || [], incoming: res.data?.incoming || [] }
  } catch {
    if (current === requestNumber) { failed.value = true; records.value = { outgoing: [], incoming: [] } }
  } finally {
    if (current === requestNumber) loading.value = false
  }
}
watch(() => props.item.id, () => { records.value = { outgoing: [], incoming: [] }; refresh() }, { immediate: true })
defineExpose({ refresh })

function roleName(person) {
  if (person.user_id === props.item.task?.assignee_user_id) return '负责人'
  if (person.user_id === props.item.task?.reviewer_user_id) return '验收人'
  return person.ptype === 'observer' ? '观察者' : '协作者'
}
function removable(person) {
  return allowed.value.includes('invite') && person.user_id !== props.item.created_by
    && person.user_id !== props.item.task?.assignee_user_id && person.user_id !== props.item.task?.reviewer_user_id
}
async function remove(person) {
  if (busy.value) return
  let reason
  try {
    const result = await ElMessageBox.prompt('移除后将取消此人的事项邀请；若本组本来可见，组内成员仍可查看。', `移除 ${person.username || '成员'}`,
      { confirmButtonText: '移除', cancelButtonText: '取消', inputPlaceholder: '填写移除原因', inputValidator: v => Boolean(v?.trim()) || '请填写原因' })
    reason = result.value.trim()
  } catch { return }
  busy.value = true
  try {
    await workService.removeParticipant(props.item.id, person.user_id, reason)
    ElMessage.success('已移除事项参与关系')
    emit('changed')
  } catch (e) { ElMessage.error(e.response?.data?.message || '移除失败，请重试') }
  finally { busy.value = false }
}
async function withdraw(row) {
  if (busy.value) return
  try { await ElMessageBox.confirm('撤回后对方将不能接单。', '撤回交付', { confirmButtonText: '撤回', cancelButtonText: '取消' }) }
  catch { return }
  busy.value = true
  try {
    await workService.decideHandoff(row.id, 'withdraw')
    ElMessage.success('已撤回交付')
    await refresh()
  } catch (e) { ElMessage.error(e.response?.data?.message || '撤回失败，请刷新查看最新状态') }
  finally { busy.value = false }
}
async function download(file) {
  if (downloading.value !== null) return
  downloading.value = file.link_id
  try { await workService.downloadFile(file.id, file.link_id, file.display_name) }
  catch (e) { ElMessage.error(e.response?.status === 404 ? '该文件当前不可访问，请刷新进度' : '下载失败，请重试') }
  finally { downloading.value = null }
}
</script>

<template>
  <DewCard size="md" variant="flat" class="collaboration-panel">
    <div class="panel-heading"><h2>协作</h2><DewButton size="sm" type="ghost" :loading="loading" @click="refresh">刷新进度</DewButton></div>
    <p v-if="item.status === 'draft'" class="hint">草稿仅你可见。发布后，即可邀请其他组成员或发起跨组交付。</p>
    <div v-else class="collaboration-options">
      <div class="collaboration-option">
        <h3>一起讨论与推进</h3>
        <p>邀请其他组成员进入同一事项，讨论、点名回应、共享附件。参与人只获得本事项的访问权。</p>
        <DewButton v-if="allowed.includes('invite')" size="sm" @click="emit('invite')">邀请成员一起协作</DewButton>
      </div>
      <div class="collaboration-option">
        <h3>请另一个组负责交付</h3>
        <p>说明需要完成的工作，由对方分管核心接单、安排执行，结果回到这里。</p>
        <DewButton v-if="allowed.includes('handoff')" size="sm" @click="emit('handoff')">请其他组承接</DewButton>
        <DewButton v-else-if="allowed.includes('promote')" size="sm" @click="emit('promote')">明确分工，转为任务</DewButton>
        <span v-else class="hint">由发起人或本组分管核心发起交付。</span>
      </div>
    </div>
    <div class="participants">
      <h3>事项成员</h3>
      <div class="participant-row"><span>{{ item.created_by_name || '发起人' }}</span><span class="hint">发起人</span></div>
      <div v-for="person in participants" :key="person.user_id" class="participant-row">
        <span>{{ person.username || `#${person.user_id}` }}</span><span class="hint">{{ roleName(person) }}</span>
        <DewButton v-if="removable(person)" size="sm" type="ghost" :disabled="busy" @click="remove(person)">移除</DewButton>
      </div>
      <p class="hint">{{ item.status === 'draft' ? '设置的负责人和验收人将在发布后加入。' : item.visibility === 'workspace' ? '本组有效成员也可查看和参与；此处列出发起人和单独加入的成员。' : '仅发起人和被邀请的参与人可见。' }}</p>
    </div>
    <div class="handoff-records">
      <h3>跨组交付进度</h3>
      <p v-if="failed" role="alert" class="hint">交付进度加载失败，请点击“刷新进度”重试。</p>
      <p v-else-if="loading && !records.outgoing.length && !records.incoming.length" class="hint">正在读取交付进度…</p>
      <template v-else>
        <article v-for="row in records.incoming" :key="`in-${row.id}`" class="handoff-row">
          <div class="handoff-heading"><strong>来自 {{ row.from_group_name }} · {{ row.kind }}</strong><DewTag size="sm">{{ row.status === 'accepted' ? '本组执行中' : statusLabels[row.status] || row.status }}</DewTag></div>
          <p class="note">{{ row.note }}</p>
          <p v-if="row.deadline" class="hint">期望完成：{{ row.deadline }}</p>
          <p v-if="row.result_note" class="note">交付结果：{{ row.result_note }}</p>
          <div v-for="file in row.files || []" :key="file.link_id" class="package-file">
            <span>{{ file.display_name }} · 固定版本 v{{ file.version_no }}</span>
            <DewButton v-if="file.can_download" size="sm" type="ghost" :loading="downloading === file.link_id" @click="download(file)">下载交付文件</DewButton>
          </div>
          <DewButton v-if="row.can_read_source" size="sm" type="ghost" @click="router.push(`/work/items/${row.item_id}`)">查看来源事项</DewButton>
        </article>
        <article v-for="row in records.outgoing" :key="`out-${row.id}`" class="handoff-row">
          <div class="handoff-heading"><strong>{{ row.to_group_name }} · {{ row.kind }}</strong><DewTag size="sm" :type="row.status === 'done' ? 'success' : 'neutral'">{{ statusLabels[row.status] || row.status }}</DewTag></div>
          <p class="note">{{ row.note }}</p>
          <p v-if="row.deadline" class="hint">期望完成：{{ row.deadline }}</p>
          <p v-if="row.result_note" class="note">交付结果：{{ row.result_note }}</p>
          <p v-for="file in row.files || []" :key="file.link_id" class="hint">已交付文件：{{ file.display_name }} · 固定版本 v{{ file.version_no }}</p>
          <DewButton v-if="row.can_read_target && row.accepted_item_id" size="sm" type="ghost" @click="router.push(`/work/items/${row.accepted_item_id}`)">查看承接任务</DewButton>
          <DewButton v-if="row.can_withdraw" size="sm" type="ghost" :disabled="busy" @click="withdraw(row)">撤回交付</DewButton>
        </article>
        <p v-if="!records.outgoing.length && !records.incoming.length" class="hint">暂无跨组交付。临时交流可直接邀请成员，无需另建交付任务。</p>
      </template>
    </div>
  </DewCard>
</template>

<style scoped>
.collaboration-panel { margin-top: 14px; }
.panel-heading, .handoff-heading, .participant-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.panel-heading { justify-content: space-between; margin-bottom: 12px; }
h2 { font-size: 15px; margin: 0; }
h3 { font-size: 13px; margin: 0 0 8px; }
.hint, .collaboration-option p { font-size: 12px; color: var(--dew-text-muted); line-height: 1.7; }
.collaboration-options { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.collaboration-option { border: 1px solid var(--el-border-color-lighter); padding: 14px; border-radius: 10px; }
.collaboration-option p { margin: 0 0 10px; }
.participants, .handoff-records { margin-top: 18px; }
.participant-row { font-size: 13px; padding: 4px 0; }
.handoff-row { border-top: 1px solid var(--el-border-color-lighter); padding: 12px 0; }
.handoff-heading { font-size: 13px; }
.package-file { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; font-size: 13px; }
.note { white-space: pre-wrap; word-break: break-word; line-height: 1.7; font-size: 13px; }
@media (max-width: 600px) { .collaboration-options { grid-template-columns: 1fr; } }
</style>
