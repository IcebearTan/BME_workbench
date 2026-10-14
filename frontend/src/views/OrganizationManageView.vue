<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { DewCard } from '@bme/dew-ui'
import api from '../api'
const members = ref([]), groups = ref([]), loading = ref(false), error = ref('')
const dialog = reactive({ visible: false, name: '', match: null, groups: [], role: 'member', reason: '', source: '', busy: false })
const message = e => e.response?.data?.error?.message || e.response?.data?.message || '操作未完成，请重试'
async function load() {
  loading.value = true; error.value = ''
  try { const { data } = await api.get('/admin/organization/members'); members.value = data.data.members; groups.value = data.data.groups }
  catch (e) { error.value = message(e); members.value = [] }
  finally { loading.value = false }
}
function open() { Object.assign(dialog, { visible: true, name: '', match: null, groups: [], role: 'member', reason: '', source: '', busy: false }) }
async function match() {
  dialog.match = null
  if (!dialog.name.trim()) return
  dialog.busy = true
  try {
    const { data } = await api.post('/admin/organization/candidates', { names: [dialog.name.trim()] })
    const found = data.data.matches[0]
    if (found.status !== 'unique_matched' || !found.resolved_user_id || found.resolved_account?.eligible !== true) return ElMessage.warning(found.message || '未找到唯一的已认证有效账号，请核对姓名或主账号')
    dialog.match = { user_id: found.resolved_user_id, person_id: found.candidates[0].person_id, name: found.candidates[0].verified_name }
  } catch (e) { ElMessage.error(message(e)) }
  finally { dialog.busy = false }
}
async function save() {
  if (!dialog.match || !dialog.groups.length || !dialog.reason.trim()) return ElMessage.warning('请先核对人员、选择小组并填写原因')
  dialog.busy = true
  try {
    await api.post('/admin/organization/members', { entries: dialog.groups.map(group_id => ({ ...dialog.match, group_id, role: dialog.role })), reason: dialog.reason.trim(), source_note: dialog.source.trim() })
    dialog.visible = false; await load(); ElMessage.success('小组任职已登记')
  } catch (e) { ElMessage.error(message(e)) }
  finally { dialog.busy = false }
}
async function end(row) {
  try {
    const { value } = await ElMessageBox.prompt('填写结束原因，原记录和其他小组任职都会保留。', '结束小组任职', { inputValidator: value => Boolean(value?.trim()) && value.length <= 200 || '原因必填，至多200字' })
    await api.post(`/admin/organization/members/${row.id}/end`, { reason: value.trim() }); await load()
  } catch (e) { if (e !== 'cancel' && e !== 'close') ElMessage.error(message(e)) }
}
onMounted(load)
</script>
<template>
  <div class="organization-manage">
    <div class="organization-heading"><div><h1>小组任职管理</h1><p>一人可加入多个小组，同一小组可有多名分管核心。小组角色与正式社团职务分开管理。</p></div><el-button type="primary" @click="open">登记小组任职</el-button></div>
    <el-alert v-if="error" :title="error" type="error" :closable="false" />
    <DewCard no-hover variant="flat">
      <el-table :data="members" v-loading="loading">
        <el-table-column label="人员" prop="username" min-width="110" />
        <el-table-column label="小组" prop="group_name" min-width="140" />
        <el-table-column label="角色" width="120"><template #default="{ row }">{{ row.role === 'coordinator' ? '分管核心' : '成员' }}</template></el-table-column>
        <el-table-column label="任期起" prop="started_on" width="120" />
        <el-table-column label="状态" width="100"><template #default="{ row }">{{ row.status === 'active' ? '在任' : `已结束 ${row.ended_on || ''}` }}</template></el-table-column>
        <el-table-column label="资料来源" prop="source_note" min-width="160" />
        <el-table-column label="操作" width="100"><template #default="{ row }"><el-button v-if="row.status === 'active'" link type="danger" @click="end(row)">结束</el-button></template></el-table-column>
      </el-table>
    </DewCard>
    <el-dialog v-model="dialog.visible" title="登记小组任职" width="min(560px, 94vw)" append-to-body>
      <el-form label-width="100px" @submit.prevent>
        <el-form-item label="认证姓名" required><el-input v-model="dialog.name" placeholder="输入核验姓名" @input="dialog.match = null"><template #append><el-button :loading="dialog.busy" @click="match">核对账号</el-button></template></el-input></el-form-item>
        <p v-if="dialog.match" class="matched-person">已确认：{{ dialog.match.name }}</p>
        <el-form-item label="小组" required><el-select v-model="dialog.groups" multiple filterable placeholder="可选择多个小组" style="width: 100%;"><el-option v-for="g in groups" :key="g.id" :label="g.name" :value="g.id" /></el-select></el-form-item>
        <el-form-item label="小组角色"><el-radio-group v-model="dialog.role"><el-radio value="member">成员</el-radio><el-radio value="coordinator">分管核心</el-radio></el-radio-group></el-form-item>
        <el-form-item label="登记原因" required><el-input v-model="dialog.reason" maxlength="200" /></el-form-item>
        <el-form-item label="资料来源"><el-input v-model="dialog.source" maxlength="500" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialog.visible = false">取消</el-button><el-button type="primary" :loading="dialog.busy" :disabled="!dialog.match || !dialog.groups.length || !dialog.reason.trim()" @click="save">保存任职</el-button></template>
    </el-dialog>
  </div>
</template>
<style scoped>
.organization-manage { padding: 24px; max-width: 1200px; margin: auto; }
.organization-heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 20px; }
h1 { margin: 0; font-size: 24px; } p { color: var(--color-text-secondary); line-height: 1.7; }
.matched-person { padding-left: 100px; }
@media (max-width: 600px) { .organization-manage { padding: 16px; } }
</style>
