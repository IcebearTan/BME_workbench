<script setup>
// 小组事项表格视图（工作台 III，替代 WorkGroupBoard 卡片流）：
// 工具栏（工作区/类型/状态组/关键词防抖 + 发起事项）+ el-table（max-height 视口锚定，仓规）
// + 后端分页。行点击进详情。数据逻辑自 WorkGroupBoard 平移（竞态守卫/三段式）。
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { DewCard, DewTag, DewButton } from '@bme/dew-ui'
import { Search, Plus } from '@element-plus/icons-vue'
import { workService, ITEM_STATUS_LABELS, ITEM_STATUS_TYPE, VISIBILITY_LABELS } from '../services/workService'
import { useWorkAccess } from '../composables/useWorkAccess'
import WorkItemCreateDialog from '../components/Work/WorkItemCreateDialog.vue'

const route = useRoute()
const router = useRouter()
const { me } = useWorkAccess()

const workspaces = computed(() => me.value?.workspaces || [])
const workspaceId = ref(null)
const kind = ref('')                 // ''=全部 / topic / task
const status = ref('')
const keyword = ref('')
const page = ref(1)
const pageSize = 20

const loading = ref(false)
const loadFailed = ref(false)
const items = ref([])
const total = ref(0)

const createVisible = ref(false)

// 竞态守卫：快速切筛选/翻页时旧请求后到不覆盖新结果
let loadSeq = 0
async function load() {
  const seq = ++loadSeq
  loading.value = true
  loadFailed.value = false
  try {
    const params = { page: page.value, page_size: pageSize }
    if (workspaceId.value) params.workspace_id = workspaceId.value
    if (kind.value) params.kind = kind.value
    if (status.value) params.status = status.value
    if (keyword.value.trim()) params.q = keyword.value.trim()
    const res = await workService.fetchItems(params)
    if (seq !== loadSeq) return      // 过期响应丢弃
    items.value = res.data?.items || []
    total.value = res.data?.total || 0
  } catch {
    if (seq !== loadSeq) return
    loadFailed.value = true
  } finally {
    if (seq === loadSeq) loading.value = false
  }
}

// 状态筛选：单一类型=精确状态；混合视图=统一显示组（话题/任务同词表）。
// value 为逗号分隔状态集（后端 in_ 查询）。
const STATUS_GROUPS = [
  { label: '进行中', value: 'open,todo,in_progress' },
  { label: '受阻', value: 'blocked' },
  { label: '待验收', value: 'review' },
  { label: '已完成', value: 'done,closed' },
  { label: '已取消', value: 'cancelled' },
  { label: '草稿', value: 'draft' },
]
const STATUS_OPTIONS = computed(() => {
  if (!kind.value) return STATUS_GROUPS          // 全部类型：统一显示组
  return kind.value === 'task'
    ? ['todo', 'in_progress', 'blocked', 'review', 'done', 'cancelled']
    : ['draft', 'open', 'closed']                // 单一类型：精确状态
})

function openItem(row) {
  router.push(`/work/items/${row.id}`)
}

// 路由 query ws= 预选工作区（组织架构页「进入工作区」入口 + 外壳切换器写回）
function wsFromQuery() {
  const ws = Number(route.query.ws) || null
  const next = workspaces.value.some(w => w.id === ws) ? ws : null
  if (next !== workspaceId.value) workspaceId.value = next
}
onMounted(() => {
  const ws = Number(route.query.ws) || null
  workspaceId.value = workspaces.value.some(w => w.id === ws) ? ws
    : (workspaces.value.length === 1 ? workspaces.value[0].id : null)
  load()
})
watch(() => route.query.ws, wsFromQuery)

// kind 切换联动：旧 kind 的状态值对新选项集无效时重置，避免「状态=todo+类型=话题」的误导性空列表
watch(kind, () => {
  // 组值（含逗号）按 value 匹配；切换类型时组值不适用则清空
  const valid = (v) => STATUS_OPTIONS.value.some((o) =>
    typeof o === 'string' ? o === v : o.value === v)
  if (status.value && !valid(status.value)) status.value = ''
})
watch([workspaceId, kind, status], () => {
  page.value = 1
  load()
})

let searchDebounce = null
watch(keyword, () => {
  clearTimeout(searchDebounce)
  searchDebounce = setTimeout(() => { page.value = 1; load() }, 400)
})
onUnmounted(() => clearTimeout(searchDebounce))
</script>

<template>
  <div class="items-table-view">
    <!-- 工具栏 -->
    <div class="filter-bar">
      <el-select v-if="workspaces.length > 1" v-model="workspaceId" style="width: 150px;"
                 placeholder="全部工作区">
        <el-option v-for="w in workspaces" :key="w.id" :label="w.group_name" :value="w.id" />
      </el-select>
      <el-select v-model="kind" style="width: 110px;" placeholder="全部类型" clearable>
        <el-option label="话题" value="topic" />
        <el-option label="任务" value="task" />
      </el-select>
      <el-select v-model="status" style="width: 110px;" placeholder="全部状态" clearable>
        <el-option v-for="s in STATUS_OPTIONS" :key="typeof s === 'string' ? s : s.value"
                   :label="typeof s === 'string' ? ITEM_STATUS_LABELS[s] : s.label"
                   :value="typeof s === 'string' ? s : s.value" />
      </el-select>
      <el-input v-model="keyword" :prefix-icon="Search" style="width: 200px;"
                placeholder="搜索标题 / 正文" clearable />
      <div class="spacer" />
      <DewButton active @click="createVisible = true">
        <el-icon :size="14"><Plus /></el-icon>
        发起事项
      </DewButton>
    </div>

    <!-- 表格（max-height 视口锚定：仓规铁律；行点击进详情） -->
    <DewCard no-hover variant="flat" class="table-card">
      <el-table :data="items" v-loading="loading" size="default"
                max-height="calc(100vh - 310px)"
                row-class-name="row-clickable" @row-click="openItem">
        <template #empty>
          <p v-if="loadFailed" class="empty-text">
            列表加载失败
            <DewButton size="sm" @click.stop="load">重试</DewButton>
          </p>
          <p v-else class="empty-text">还没有相关工作事项；需要讨论或执行时，从右上角「发起事项」开始</p>
        </template>
        <el-table-column label="标题" min-width="260">
          <template #default="{ row }">
            <div class="title-cell">
              <span v-if="row.unread" class="unread-dot" />
              <span class="cell-title">{{ row.title }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="70">
          <template #default="{ row }">{{ row.kind === 'task' ? '任务' : '话题' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="96">
          <template #default="{ row }">
            <DewTag :type="ITEM_STATUS_TYPE[row.status] || 'neutral'" size="sm" round>
              {{ ITEM_STATUS_LABELS[row.status] || row.status }}
            </DewTag>
          </template>
        </el-table-column>
        <el-table-column label="可见范围" width="88">
          <template #default="{ row }">{{ VISIBILITY_LABELS[row.visibility] || row.visibility }}</template>
        </el-table-column>
        <el-table-column label="负责人" width="96" show-overflow-tooltip>
          <template #default="{ row }">{{ row.task?.assignee_name || '—' }}</template>
        </el-table-column>
        <el-table-column label="截止" width="132">
          <template #default="{ row }">
            <span v-if="row.kind === 'task' && row.task?.due_at" class="ws-num"
                  :class="{ 'due--overdue': row.task.overdue }">
              {{ row.task.due_at }}{{ row.task.overdue ? '（逾期）' : '' }}
            </span>
            <span v-else>—</span>
          </template>
        </el-table-column>
        <el-table-column label="回复" width="64" align="center">
          <template #default="{ row }">
            <span class="ws-num">{{ row.reply_count }}</span>
          </template>
        </el-table-column>
        <el-table-column label="最后活动" width="136" show-overflow-tooltip>
          <template #default="{ row }">{{ row.last_activity_at }}</template>
        </el-table-column>
      </el-table>
      <div v-if="total > pageSize" class="pagination-row">
        <el-pagination background layout="prev, pager, next, total" :total="total" :page-size="pageSize"
                       :current-page="page" @current-change="(p) => { page = p; load() }" />
      </div>
    </DewCard>

    <WorkItemCreateDialog v-model="createVisible" :workspaces="workspaces"
                          :default-workspace-id="workspaceId" @created="load" />
  </div>
</template>

<style scoped>
.filter-bar {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  margin-bottom: 14px;
}
.spacer { flex: 1; }

.table-card :deep(.dew-card__body) { padding: 0; }
.table-card :deep(.row-clickable) { cursor: pointer; }

.title-cell { display: flex; align-items: center; gap: 6px; min-width: 0; }
.cell-title { font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.unread-dot {
  width: 8px; height: 8px; border-radius: 50%; flex: none;
  background: var(--el-color-danger, #f56c6c);
}
.due--overdue { color: var(--el-color-danger, #f56c6c); font-weight: 600; }

.pagination-row { display: flex; justify-content: flex-end; padding: 10px 14px; }
.empty-text { margin: 4px 0; font-size: 13px; color: var(--dew-text-muted); }

@media (max-width: 768px) {
  .filter-bar { gap: 8px; }
  .filter-bar :deep(.el-input), .filter-bar :deep(.el-select) { width: 130px !important; }
  .pagination-row { justify-content: center; }
}
</style>
