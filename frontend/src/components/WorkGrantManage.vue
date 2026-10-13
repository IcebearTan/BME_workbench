<template>
  <div class="selectable">
    <div class="page-header">
      <div>
        <div class="page-title">协作授权</div>
        <div class="page-subtitle-inline">内部工作台的授权与工作区治理（依据=在任任职或组归属，资格不等于权限）</div>
      </div>
      <div class="header-actions">
        <el-button @click="fetchAll" :loading="loading">刷新</el-button>
      </div>
    </div>
    <p class="page-subtitle">
      授权岗位仅三档：组员（本组工作人员）/ 协调员（本组分派与验收协调）/ 治理（全局授权管理，仅工作台管理员可授）。
      开启「入职自动授」的工作区：组归属/任职建档即自动开通对应岗位授权，卸任/调组/退组自动失效——
      手动开通的授权优先；撤销时可勾选「同时否决」阻止该成员再自动获得授权。
    </p>

    <!-- 工作区管理 -->
    <DewCard no-hover class="table-card">
      <template #header>
        <div class="card-head">
          <span>组工作区</span>
          <span class="card-head-hint">一组最多一个；停用=入口关闸，数据与授权记录保留</span>
        </div>
      </template>
      <el-table :data="workspaces" v-loading="loading" style="width: 100%"
                max-height="calc(100vh - 320px)">
        <el-table-column label="组别" min-width="160">
          <template #default="{ row }">
            <span>{{ row.group_name }}</span>
            <span class="option-id">#{{ row.club_group_id }}</span>
          </template>
        </el-table-column>
        <el-table-column label="工作区状态" width="110">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
              {{ row.status === 'active' ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="group_status" label="组状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.group_status === 'active' ? '' : 'info'" size="small">
              {{ row.group_status === 'active' ? '启用' : '已归档' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="入职自动授" width="110">
          <template #default="{ row }">
            <el-switch :model-value="row.auto_grant" :disabled="row.status !== 'active'"
                       :loading="autoGrantSaving === row.id"
                       @change="(v) => toggleAutoGrant(row, v)" />
          </template>
        </el-table-column>
        <el-table-column prop="active_grants" label="有效授权" width="90" />
        <el-table-column label="操作" width="110" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.status === 'active'" size="small" type="warning" plain
                       @click="toggleWorkspace(row, 'disabled')">停用</el-button>
            <el-button v-else size="small" type="success" plain
                       @click="toggleWorkspace(row, 'active')">启用</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="open-ws-row">
        <el-cascader v-model="newWsGroup" :options="openableGroupOptions" :props="cascaderProps"
                     placeholder="选择要开通工作区的启用组" clearable style="width: 320px;" />
        <el-checkbox v-model="newWsAuto">入职自动授（建区即按现任归属/任职批量开通）</el-checkbox>
        <el-button type="primary" :disabled="!newWsGroup" :loading="wsSaving" @click="openWorkspace">开通工作区</el-button>
      </div>
      <div v-if="!hasClubWs" class="open-ws-row" style="margin-top: 8px;">
        <span class="open-ws-club-hint">社团工作区（全社公告与讨论，开通后自动授全部在任干事与各组组长）</span>
        <el-button :loading="clubWsSaving" @click="openClubWorkspace">开通社团工作区</el-button>
      </div>
    </DewCard>

    <!-- 开通授权 + 授权记录 + 撤销（拆分组件 GrantListSection） -->
    <GrantListSection ref="grantListRef" :users="users" :users-loading="usersLoading"
                      :workspaces="workspaces" @changed="fetchWorkspaces" />

    <!-- 治理工具：接管队列/交接清单/紧急介入（拆分组件 GovToolsSection） -->
    <GovToolsSection ref="govToolsRef" :users="users" :users-loading="usersLoading" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import '../styles/admin-pages.css'
import { ElMessage, ElMessageBox } from 'element-plus'
import { DewCard } from '@bme/dew-ui'
import api from '../api'
import { buildGroupCascaderOptions } from '../utils/club'
import GrantListSection from './GrantListSection.vue'
import GovToolsSection from './GovToolsSection.vue'

// ── 基础数据 ──
const loading = ref(false)
const users = ref([])
const usersLoading = ref(false)
const groupOptions = ref([])
const workspaces = ref([])
const cascaderProps = { checkStrictly: true, emitPath: false }
const grantListRef = ref(null)
const govToolsRef = ref(null)

const fetchUsers = async () => {
  usersLoading.value = true
  try {
    const res = await api({ url: '/user/user_list', method: 'get' })
    users.value = res.data || []
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '获取用户名单失败')
  } finally {
    usersLoading.value = false
  }
}

const fetchGroups = async () => {
  try {
    const res = await api({ url: '/admin/club/groups', method: 'get' })
    groupOptions.value = buildGroupCascaderOptions(res.data?.data?.groups || [])
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '获取组树失败')
  }
}

const fetchWorkspaces = async () => {
  try {
    const res = await api({ url: '/work/governance/workspaces', method: 'get' })
    workspaces.value = res.data?.data?.workspaces || []
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '获取工作区列表失败')
  }
}

// 已开通工作区的组不再出现在开通选择里
const openableGroupOptions = computed(() => {
  const opened = new Set(workspaces.value.map(w => w.club_group_id))
  const walk = (nodes) => nodes
    .filter(n => !opened.has(n.value))
    .map(n => ({ ...n, children: n.children ? walk(n.children) : undefined }))
    .map(n => ({ ...n, children: n.children?.length ? n.children : undefined }))
  return walk(groupOptions.value)
})

// ── 工作区开通与启停 ──
const newWsGroup = ref(null)
const newWsAuto = ref(true)
const wsSaving = ref(false)
const clubWsSaving = ref(false)
const hasClubWs = computed(() => workspaces.value.some(w => w.scope === 'club'))

const openClubWorkspace = async () => {
  try {
    await ElMessageBox.confirm(
      '开通社团工作区？范围=全社公告与讨论，自动授权全部在任干事与各组组长（组长类为协调员）。',
      '开通社团工作区', { confirmButtonText: '开通', cancelButtonText: '取消' })
  } catch { return }
  clubWsSaving.value = true
  try {
    const res = await api({ url: '/work/governance/workspaces', method: 'post',
                            data: { scope: 'club', auto_grant: true } })
    ElMessage.success(res.data?.message || '社团工作区已开通')
    grantListRef.value?.fetchGrants()
    await fetchWorkspaces()
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '开通失败')
  } finally {
    clubWsSaving.value = false
  }
}

const openWorkspace = async () => {
  if (!newWsGroup.value) return
  wsSaving.value = true
  try {
    const res = await api({ url: '/work/governance/workspaces', method: 'post',
                            data: { club_group_id: newWsGroup.value, auto_grant: newWsAuto.value } })
    ElMessage.success(res.data?.message || '工作区已开通')
    newWsGroup.value = null
    grantListRef.value?.fetchGrants()
    await fetchWorkspaces()
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '开通失败')
  } finally {
    wsSaving.value = false
  }
}

// ── 入职自动授开关（关=只停新增；开=按现任组织行批量补授） ──
const autoGrantSaving = ref(null)
const toggleAutoGrant = async (row, enabled) => {
  try {
    await ElMessageBox.confirm(
      enabled
        ? `开启「${row.group_name}」入职自动授：将按现任归属/任职批量开通授权（已有授权不重复）。确认开启？`
        : `关闭「${row.group_name}」入职自动授：此后新入组成员不再自动获得授权（存量授权保留）。确认关闭？`,
      enabled ? '开启自动授' : '关闭自动授',
      { confirmButtonText: enabled ? '开启' : '关闭', cancelButtonText: '取消' })
  } catch { return }
  autoGrantSaving.value = row.id
  try {
    const res = await api({ url: `/work/governance/workspaces/${row.id}/auto-grant`,
                            method: 'post', data: { enabled } })
    ElMessage.success(res.data?.message || '已调整')
    grantListRef.value?.fetchGrants()
    await fetchWorkspaces()
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '调整失败')
  } finally {
    autoGrantSaving.value = null
  }
}

const toggleWorkspace = async (row, status) => {
  const action = status === 'disabled' ? '停用' : '启用'
  try {
    await ElMessageBox.confirm(
      status === 'disabled'
        ? `停用「${row.group_name}」工作区后，成员将无法进入（数据与授权记录保留）。确认停用？`
        : `重新启用「${row.group_name}」工作区？`,
      `${action}工作区`, { confirmButtonText: action, cancelButtonText: '取消' })
  } catch { return }
  try {
    const res = await api({ url: `/work/governance/workspaces/${row.id}/status`, method: 'post',
                            data: { status } })
    ElMessage.success(res.data?.message || `已${action}`)
    await fetchWorkspaces()
  } catch (e) {
    ElMessage.error(e.response?.data?.message || `${action}失败`)
  }
}

const fetchAll = async () => {
  loading.value = true
  await Promise.allSettled([
    fetchWorkspaces(),
    grantListRef.value?.fetchGrants(),
    govToolsRef.value?.fetchTakeover(),
  ])
  loading.value = false
}

onMounted(() => {
  fetchUsers()
  fetchGroups()
  fetchAll()
})
</script>

<style scoped>
.open-ws-club-hint {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  margin-right: 12px;
}
.page-subtitle {
  margin: -12px 0 16px;
  font-size: 12.5px;
  color: var(--el-text-color-secondary);
  line-height: 1.6;
}

.page-subtitle-inline { margin-top: 4px; font-size: var(--text-sm); color: var(--el-text-color-secondary); }

.table-card { margin-bottom: 16px; }
.table-card :deep(.dew-card__body) { padding: 16px; }

.card-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.card-head-hint { font-size: 12px; color: var(--el-text-color-secondary); font-weight: 400; }

.open-ws-row { display: flex; align-items: center; gap: 12px; margin-top: 12px; }

.option-id { margin-left: 6px; color: var(--el-text-color-secondary); font-size: 12px; }
</style>
