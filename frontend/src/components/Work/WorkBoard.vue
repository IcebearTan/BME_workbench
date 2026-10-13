<script setup>
// 工作区「看板」tab（X2 通用投影）：按关联对象聚合本组事项态势。
// 行卡=对象名+安全字段 chips+未完结/逾期徽标+认领状态——组件不认识任何业务。
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { DewCard, DewTag, DewSkeleton, DewButton } from '@bme/dew-ui'
import { DataBoard } from '@element-plus/icons-vue'
import { workService } from '../../services/workService'
import { useWorkAccess } from '../../composables/useWorkAccess'

const route = useRoute()
const { me } = useWorkAccess()
const workspaces = computed(() => (me.value?.workspaces || [])
  .filter(w => w.status === 'active'))
const myRole = computed(() => {
  const wsId = workspaceId.value
  const w = workspaces.value.find(x => x.id === wsId)
  return w?.role || 'member'
})

const workspaceId = ref(null)
const loading = ref(true)
const loadFailed = ref(false)
const board = ref(null)
const claiming = ref(null)

// 竞态守卫
let loadSeq = 0
async function load() {
  const seq = ++loadSeq
  loading.value = true
  loadFailed.value = false
  try {
    const res = await workService.fetchBoard(workspaceId.value)
    if (seq !== loadSeq) return
    board.value = res.data
  } catch {
    if (seq !== loadSeq) return
    loadFailed.value = true
  } finally {
    if (seq === loadSeq) loading.value = false
  }
}

async function toggleClaim(row) {
  if (claiming.value) return
  claiming.value = `${row.source_type}:${row.source_id}`
  try {
    const action = row.claimed ? 'unclaim' : 'claim'
    const res = await workService.claimObject({
      source_type: row.source_type, source_id: row.source_id,
      ws_id: workspaceId.value, action,
    })
    ElMessage.success(res.message || '已处理')
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '操作失败')
  } finally { claiming.value = null }
}

const fieldsOf = (row) => Object.entries(row.fields || {}).filter(([k]) => k !== 'title')

onMounted(() => {
  const ws = Number(route.query.ws) || null
  workspaceId.value = workspaces.value.some(w => w.id === ws) ? ws
    : (workspaces.value[0]?.id || null)
  if (workspaceId.value) load()
  else loading.value = false
})
watch(workspaceId, () => { if (workspaceId.value) load() })
// 外壳工作区切换器写回 ?ws= 时联动（看板必须有具体工作区，空值回落第一个）
watch(() => route.query.ws, () => {
  const ws = Number(route.query.ws) || null
  const next = workspaces.value.some(w => w.id === ws) ? ws
    : (workspaces.value[0]?.id || null)
  if (next !== workspaceId.value) workspaceId.value = next
})
</script>

<template>
  <div class="board">
    <div class="filter-bar">
      <el-select v-if="workspaces.length > 1" v-model="workspaceId" style="width: 160px;">
        <el-option v-for="w in workspaces" :key="w.id" :label="w.group_name" :value="w.id" />
      </el-select>
      <span class="hint">本组认领与引用的对象 × 事项态势；认领=登记维护责任，不改变原业务权限</span>
    </div>

    <template v-if="loading">
      <DewCard v-for="i in 3" :key="i" size="md" variant="flat"><DewSkeleton variant="text" :lines="2" /></DewCard>
    </template>
    <DewCard v-else-if="loadFailed" size="md" variant="flat">
      <p class="empty-text">看板加载失败，请重试</p>
      <DewButton size="sm" :loading="loading" @click="load">重试</DewButton>
    </DewCard>
    <DewCard v-else-if="!board?.objects?.length" size="md" variant="flat">
      <p class="empty-text">
        还没有关联对象；在事项里「添加关联」（课程/营期/工单），或让协调员认领本组负责的对象后，这里会显示每个对象的工作态势
      </p>
    </DewCard>

    <template v-else>
      <DewCard v-for="row in board.objects" :key="`${row.source_type}:${row.source_id}`"
               size="md" variant="flat" class="obj-card">
        <div class="obj-row">
          <el-icon class="obj-icon" :size="16"><DataBoard /></el-icon>
          <div class="obj-main">
            <div class="obj-title-line">
              <DewTag type="neutral" size="sm" round>{{ row.label }}</DewTag>
              <span class="obj-name">{{ row.accessible ? row.title : '不可访问对象' }}</span>
              <DewTag v-if="row.claimed" type="primary" size="sm" round>已认领</DewTag>
              <DewTag v-else-if="row.active_items > 0" type="warning" size="sm" round>未认领</DewTag>
            </div>
            <div class="obj-meta">
              <span v-for="[k, v] in fieldsOf(row)" :key="k" class="obj-field">{{ k }}：{{ v ?? '—' }}</span>
              <span v-if="row.last_activity" class="obj-field">最近活动 {{ row.last_activity }}</span>
            </div>
          </div>
          <div class="obj-stats">
            <div class="stat" :class="{ 'stat--hot': row.active_items > 0 }">
              <span class="stat-num">{{ row.active_items }}</span>
              <span class="stat-label">未完结</span>
            </div>
            <div class="stat" :class="{ 'stat--hot': row.overdue_items > 0 }">
              <span class="stat-num">{{ row.overdue_items }}</span>
              <span class="stat-label">逾期</span>
            </div>
          </div>
          <DewButton v-if="myRole === 'coordinator' && board.stewardable_types?.includes(row.source_type)"
                     size="sm" :type="row.claimed ? 'ghost' : 'active'"
                     :loading="claiming === `${row.source_type}:${row.source_id}`"
                     @click="toggleClaim(row)">
            {{ row.claimed ? '取消认领' : '认领' }}
          </DewButton>
        </div>
      </DewCard>
    </template>
  </div>
</template>

<style scoped>
.filter-bar { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; flex-wrap: wrap; }
.hint { font-size: 12px; color: var(--dew-text-muted); }
.obj-card { margin-bottom: 10px; }
.obj-row { display: flex; align-items: center; gap: 12px; }
.obj-icon { color: var(--dew-text-muted); flex: none; }
.obj-main { flex: 1; min-width: 0; }
.obj-title-line { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.obj-name { font-size: 14px; font-weight: 600; }
.obj-meta { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 4px; }
.obj-field { font-size: 12px; color: var(--dew-text-muted); }
.obj-stats { display: flex; gap: 14px; flex: none; }
.stat { display: flex; flex-direction: column; align-items: center; min-width: 44px; }
.stat-num { font-size: 18px; font-weight: 700; font-variant-numeric: tabular-nums; }
.stat--hot .stat-num { color: var(--el-color-danger, #f56c6c); }
.stat-label { font-size: 11px; color: var(--dew-text-muted); }
.empty-text { margin: 4px 0 10px; font-size: 13px; color: var(--dew-text-muted); }
@media (max-width: 768px) {
  .obj-row { flex-wrap: wrap; }
  .obj-stats { width: 100%; flex-direction: row; justify-content: flex-start; }
}
</style>
