<template>
  <div>
    <!-- 开通授权 -->
    <DewCard no-hover class="table-card">
      <template #header>
        <div class="card-head"><span>开通授权</span></div>
      </template>
      <el-form class="grant-form" label-width="90px" style="max-width: 640px;">
        <el-form-item label="成员" required>
          <el-select v-model="form.userId" filterable placeholder="搜索并选择社员" style="width: 100%;"
                     :loading="usersLoading" @change="onUserChange">
            <el-option v-for="u in users" :key="u.User_Id" :label="u.User_Name" :value="u.User_Id">
              <span>{{ u.User_Name }}</span>
              <span class="option-id">#{{ u.User_Id }}</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="岗位" required>
          <el-radio-group v-model="form.role">
            <el-radio-button value="member">组员</el-radio-button>
            <el-radio-button value="coordinator">协调员</el-radio-button>
            <el-radio-button value="governance">治理</el-radio-button>
          </el-radio-group>
          <div v-if="form.role === 'governance'" class="form-hint">
            全局治理岗位，仅工作台管理员可授（治理人员不能再授予治理岗位）
          </div>
          <div v-if="form.role === 'coordinator'" class="form-hint">
            <el-checkbox v-model="form.subtree">含子组汇总（仅摘要级：子组事项的标题/状态/负责人/截止，不含正文）</el-checkbox>
          </div>
        </el-form-item>
        <el-form-item v-if="form.role !== 'governance'" label="工作区" required>
          <el-select v-model="form.workspaceId" placeholder="选择组工作区" style="width: 100%;"
                     :disabled="!form.userId">
            <el-option v-for="w in workspaces" :key="w.id" :label="w.group_name" :value="w.id" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.role !== 'governance'" label="授权依据" required>
          <div v-if="!form.userId" class="form-hint">先选择成员</div>
          <template v-else>
            <!-- 依据数据源独立失败态：不能伪装成「该成员无资格」 -->
            <div v-if="officersFailed" class="form-hint form-hint--warn source-fail">
              授权依据（在任任职）加载失败，请刷新
              <el-button link type="primary" @click="fetchOfficers">重新加载</el-button>
            </div>
            <template v-else>
              <div v-if="officersTruncated" class="form-hint form-hint--warn">
                在任干事超过 100 条，仅显示前 100 条，请通过成员搜索定位后核对任职依据
              </div>
              <div v-if="!sourceOptions.length" class="form-hint form-hint--warn">
                该成员无在任任职或组归属，不能作为授权依据（先在「任职管理/成员归属」建档）
              </div>
            </template>
            <el-radio-group v-if="sourceOptions.length" v-model="form.sourceKey">
              <el-radio v-for="s in sourceOptions" :key="s.key" :value="s.key">{{ s.label }}</el-radio>
            </el-radio-group>
          </template>
        </el-form-item>
        <el-form-item label="有效期至">
          <el-date-picker v-model="form.validUntil" type="date" placeholder="可不填（跟随任职/归属）"
                          value-format="YYYY-MM-DD" style="width: 220px;" />
        </el-form-item>
        <el-form-item label="授权原因" required>
          <el-input v-model="form.grantReason" maxlength="200" show-word-limit
                    placeholder="如：运行保障组值班开通 / 培训组负责人" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="saving" :disabled="!canSubmit" @click="submitGrant">开通授权</el-button>
        </el-form-item>
      </el-form>
    </DewCard>

    <!-- 授权记录 -->
    <DewCard no-hover class="table-card">
      <template #header>
        <div class="card-head">
          <span>授权记录</span>
          <div class="filter-row">
            <el-select v-model="query.status" style="width: 110px;" @change="onFilterChange">
              <el-option label="全部" value="all" />
              <el-option label="生效中" value="active" />
              <el-option label="已撤销" value="revoked" />
              <el-option label="已否决" value="vetoed" />
            </el-select>
            <el-select v-model="query.workspaceId" clearable placeholder="全部工作区" style="width: 160px;"
                       @change="onFilterChange">
              <el-option v-for="w in workspaces" :key="w.id" :label="w.group_name" :value="w.id" />
            </el-select>
          </div>
        </div>
      </template>
      <el-table :data="grants" v-loading="grantsLoading" style="width: 100%"
                max-height="calc(100vh - 320px)">
        <el-table-column label="成员" min-width="120">
          <template #default="{ row }">{{ row.username }}<span class="option-id">#{{ row.user_id }}</span></template>
        </el-table-column>
        <el-table-column label="岗位" width="90">
          <template #default="{ row }">{{ ROLE_LABELS[row.role] || row.role }}</template>
        </el-table-column>
        <el-table-column label="工作区" min-width="110">
          <template #default="{ row }">{{ row.workspace_id ? row.workspace_group_name : '全局' }}</template>
        </el-table-column>
        <el-table-column label="依据" min-width="120">
          <template #default="{ row }">{{ SOURCE_LABELS[row.source_type] || row.source_type }}</template>
        </el-table-column>
        <el-table-column label="来源" width="76">
          <template #default="{ row }">
            <el-tag :type="row.origin === 'auto' ? 'info' : ''" size="small" effect="plain">
              {{ row.origin === 'auto' ? '自动' : '手动' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="有效期" width="100">
          <template #default="{ row }">{{ row.valid_until || '不限' }}</template>
        </el-table-column>
        <el-table-column label="状态" min-width="130">
          <template #default="{ row }">
            <el-tooltip v-if="row.status === 'active' && !row.effective" :content="row.ineffective_reason"
                        placement="top">
              <el-tag type="warning" size="small">已失效：{{ row.ineffective_reason }}</el-tag>
            </el-tooltip>
            <el-tag v-else-if="row.status === 'active'" type="success" size="small">生效中</el-tag>
            <el-tooltip v-else-if="row.status === 'vetoed'" :content="row.revoke_reason || ''" placement="top">
              <el-tag type="danger" size="small">已否决（不再自动授）</el-tag>
            </el-tooltip>
            <el-tag v-else type="info" size="small">已撤销</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="grant_reason" label="原因" min-width="140" show-overflow-tooltip />
        <el-table-column prop="created_at" label="授予时间" width="110" />
        <el-table-column label="操作" width="104" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.status === 'active'" size="small" type="danger" plain @click="openRevoke(row)">
              撤销
            </el-button>
            <el-button v-else-if="row.status === 'vetoed'" size="small" type="warning" plain
                       @click="unveto(row)">解除否决</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrapper">
        <el-pagination background layout="total, prev, pager, next" :total="total"
                       :page-size="query.pageSize" :current-page="query.page"
                       @current-change="onPageChange" />
      </div>
    </DewCard>

    <!-- 撤销弹窗（头部含撤销对象摘要，防误操作） -->
    <el-dialog v-model="revokeVisible" title="撤销授权" width="440px">
      <div v-if="revokeTarget" class="revoke-summary">
        <div class="revoke-summary-main">
          <span class="revoke-summary-name">{{ revokeTarget.username }}</span>
          <span class="option-id">#{{ revokeTarget.user_id }}</span>
        </div>
        <div class="revoke-summary-meta">
          {{ ROLE_LABELS[revokeTarget.role] || revokeTarget.role }} ·
          {{ revokeTarget.workspace_id ? revokeTarget.workspace_group_name : '全局' }} ·
          依据：{{ SOURCE_LABELS[revokeTarget.source_type] || revokeTarget.source_type }}
        </div>
        <div v-if="revokeTarget.ineffective_reason" class="revoke-summary-reason">
          当前已失效：{{ revokeTarget.ineffective_reason }}（撤销后记录归档）
        </div>
      </div>
      <p class="dialog-text">撤销即时生效（该成员下一请求即失去权限）。请填写撤销原因（必填）：</p>
      <el-input v-model="revokeReason" type="textarea" :rows="3" maxlength="200" show-word-limit
                placeholder="请填写撤销原因（必填）" />
      <el-checkbox v-if="revokeTarget?.workspace_id" v-model="revokeVeto" class="dialog-veto">
        同时否决：该成员本工作区不再自动获得授权（退社再入社也不复活）
      </el-checkbox>
      <!-- 操作区放主体尾部而非 #footer slot：本仓 e2e 环境下子组件 dialog 的 footer slot
           事件挂载不生效（主体 slot 与 EP 自绘的头部 X 均正常，逐层验证见 2026-09-30 排查） -->
      <div class="dialog-actions">
        <el-button @click="revokeVisible = false">取消</el-button>
        <el-button type="danger" :loading="revoking" :disabled="!revokeReason.trim()" @click="confirmRevoke">
          {{ revokeVeto ? '撤销并否决' : '确认撤销' }}
        </el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { DewCard } from '@bme/dew-ui'
import api from '../api'

defineProps({
  /** 成员名单（主页面统一拉取） */
  users: { type: Array, default: () => [] },
  usersLoading: { type: Boolean, default: false },
  /** 工作区列表（表单选择与筛选项共用） */
  workspaces: { type: Array, default: () => [] },
})
const emit = defineEmits(['changed'])

const ROLE_LABELS = { member: '组员', coordinator: '协调员', governance: '治理' }
const SOURCE_LABELS = { officer: '在任任职', membership: '组归属', internal_membership: '小组任职', direct: '直接授予' }

// ── 开通授权表单 ──
const form = reactive({
  userId: null, role: 'member', workspaceId: null,
  sourceKey: '', validUntil: null, grantReason: '',
  subtree: false,
})
const officerRows = ref([])          // 在任任职（一次取前 100 条）
const officersTotal = ref(0)
const officersFailed = ref(false)
const userMembership = ref({ primary: null, secondary: null })
const saving = ref(false)

// 授权依据选项：在任任职行 + 归属行（membership_id 为来源行 id）
const sourceOptions = computed(() => {
  if (!form.userId) return []
  const opts = []
  for (const o of officerRows.value) {
    if (o.user_id === form.userId) {
      opts.push({ key: `officer:${o.id}`, source_type: 'officer', source_id: o.id,
                  label: `任职：${o.title}${o.department ? ' · ' + o.department : ''}` })
    }
  }
  for (const slot of ['primary', 'secondary']) {
    const m = userMembership.value[slot]
    if (m?.membership_id) {
      opts.push({ key: `membership:${m.membership_id}`, source_type: 'membership',
                  source_id: m.membership_id, label: `组归属：${m.name}（${slot === 'primary' ? '主要' : '次要'}）` })
    }
  }
  return opts
})

const fetchOfficers = async () => {
  officersFailed.value = false
  try {
    const res = await api({ url: '/admin/officers', method: 'get',
                            params: { status: 'active', per_page: 100 } })
    officerRows.value = res.data?.data?.officers || []
    officersTotal.value = res.data?.data?.total || 0
  } catch {
    officerRows.value = []
    officersTotal.value = 0
    officersFailed.value = true   // 独立失败态，不再伪装成「无资格」
  }
}

// 拉满 100 条即截断：提示按成员搜索定位，而不是静默缺依据
const officersTruncated = computed(() => officersTotal.value > officerRows.value.length)

const onUserChange = async (uid) => {
  form.sourceKey = ''
  userMembership.value = { primary: null, secondary: null }
  if (!uid) return
  try {
    const res = await api({ url: `/admin/club/membership/${uid}`, method: 'get' })
    userMembership.value = res.data?.data || { primary: null, secondary: null }
  } catch { /* 依据选项留空 */ }
}

const selectedSource = computed(() => sourceOptions.value.find(s => s.key === form.sourceKey))
const canSubmit = computed(() => {
  if (!form.userId || !form.grantReason.trim()) return false
  if (form.role === 'governance') return true
  return Boolean(form.workspaceId) && Boolean(selectedSource.value)
})

const submitGrant = async () => {
  saving.value = true
  try {
    const payload = {
      user_id: form.userId, role: form.role, subtree: !!form.subtree, grant_reason: form.grantReason.trim(),
      valid_until: form.validUntil || null,
    }
    if (form.role === 'governance') {
      payload.source_type = 'direct'
    } else {
      payload.workspace_id = form.workspaceId
      payload.source_type = selectedSource.value.source_type
      payload.source_id = selectedSource.value.source_id
    }
    const res = await api({ url: '/work/governance/grants', method: 'post', data: payload })
    ElMessage.success(res.data?.message || '授权已开通')
    form.grantReason = ''
    emit('changed')          // 新增授权会改变工作区有效授权计数
    await fetchGrants()
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '开通失败')
  } finally {
    saving.value = false
  }
}

// ── 授权记录与撤销 ──
const grants = ref([])
const grantsLoading = ref(false)
const total = ref(0)
const query = reactive({ page: 1, pageSize: 20, status: 'all', workspaceId: null })

const fetchGrants = async () => {
  grantsLoading.value = true
  try {
    const params = { page: query.page, page_size: query.pageSize, status: query.status }
    if (query.workspaceId) params.workspace_id = query.workspaceId
    const res = await api({ url: '/work/governance/grants', method: 'get', params })
    grants.value = res.data?.data?.grants || []
    total.value = res.data?.data?.total || 0
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '获取授权记录失败')
  } finally {
    grantsLoading.value = false
  }
}

// 筛选变更先重置页码再拉取（第 3 页改筛选不再落在空页）
const onFilterChange = () => {
  query.page = 1
  fetchGrants()
}

const onPageChange = (p) => {
  query.page = p
  fetchGrants()
}

const revokeVisible = ref(false)
const revokeReason = ref('')
const revokeVeto = ref(false)
const revoking = ref(false)
const revokeTarget = ref(null)

const openRevoke = (row) => {
  revokeTarget.value = row
  revokeReason.value = ''
  revokeVeto.value = false
  revokeVisible.value = true
}

const confirmRevoke = async () => {
  revoking.value = true
  try {
    const res = await api({ url: `/work/governance/grants/${revokeTarget.value.id}/revoke`,
                            method: 'post',
                            data: { reason: revokeReason.value.trim(), veto: revokeVeto.value } })
    ElMessage.success(res.data?.message || '已撤销')
    revokeVisible.value = false
    emit('changed')          // 工作区有效授权计数需要刷新，由主页面处理
    await fetchGrants()
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '撤销失败')
  } finally {
    revoking.value = false
  }
}

// 解除否决：vetoed→revoked，并按当前组织事实重算（人在组里则当场恢复权限）
const unveto = async (row) => {
  try {
    await ElMessageBox.confirm(
      `解除对 ${row.username}（${row.workspace_group_name || '全局'}）的否决？解除后若组织事实仍命中，将自动恢复其本工作区授权。`,
      '解除否决', { confirmButtonText: '解除否决', cancelButtonText: '取消' })
  } catch { return }
  try {
    const res = await api({ url: `/work/governance/grants/${row.id}/unveto`, method: 'post' })
    ElMessage.success(res.data?.message || '已解除否决')
    emit('changed')
    await fetchGrants()
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '解除失败')
  }
}

onMounted(() => {
  fetchOfficers()      // 授权记录首拉由主页面的 fetchAll 统一触发
})

defineExpose({ fetchGrants })
</script>

<style scoped>
.table-card { margin-bottom: 16px; }
.table-card :deep(.dew-card__body) { padding: 16px; }

.card-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.filter-row { display: flex; gap: 8px; }

.option-id { margin-left: 6px; color: var(--el-text-color-secondary); font-size: 12px; }

.form-hint { font-size: 12px; color: var(--el-text-color-secondary); line-height: 1.6; }
.form-hint--warn { color: var(--el-color-warning); }
.source-fail { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }

.dialog-text { margin: 0 0 10px; font-size: 13px; color: var(--el-text-color-regular); line-height: 1.6; }
.dialog-veto { margin: 10px 0 0; }

.revoke-summary {
  margin-bottom: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--el-fill-color-light);
}
.revoke-summary-name { font-weight: 600; }
.revoke-summary-meta { margin-top: 2px; font-size: 12.5px; color: var(--el-text-color-secondary); }
.revoke-summary-reason { margin-top: 4px; font-size: 12.5px; color: var(--el-color-warning); }
</style>
