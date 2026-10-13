<script setup>
// 子组汇总（跨组方案 §4.1，X1）：subtree 授权者的态势视图。
// 摘要=标题/类型/状态/负责人/截止（无正文）；受限事项只显示占位；
// 点卡片提示「内容需该组邀请」——摘要层永远不进正文。
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { DewCard, DewTag, DewSkeleton, DewButton } from '@bme/dew-ui'
import { Search, Lock } from '@element-plus/icons-vue'
import { workService, ITEM_STATUS_LABELS, ITEM_STATUS_TYPE } from '../../services/workService'

const keyword = ref('')
const loading = ref(true)
const loadFailed = ref(false)
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20

// 竞态守卫：快速输入/翻页时旧请求后到不覆盖新结果
let loadSeq = 0
async function load() {
  const seq = ++loadSeq
  loading.value = true
  loadFailed.value = false
  try {
    const params = { page: page.value, page_size: pageSize }
    if (keyword.value.trim()) params.q = keyword.value.trim()
    const res = await workService.fetchSummaryItems(params)
    if (seq !== loadSeq) return
    items.value = res.data?.items || []
    total.value = res.data?.total || 0
  } catch (e) {
    if (seq !== loadSeq) return
    loadFailed.value = true
  } finally {
    if (seq === loadSeq) loading.value = false
  }
}

let debounce = null

function onCardClick(item) {
  if (item.restricted) {
    ElMessage.info('该事项为受限内容，需该组邀请后才能查看')
    return
  }
  ElMessage.info('摘要层不提供正文入口；需查看内容请让该组协调员邀请你参与')
}

onMounted(load)
</script>

<template>
  <div class="summary-board">
    <div class="filter-bar">
      <el-input v-model="keyword" :prefix-icon="Search" style="width: 240px;"
                placeholder="按标题搜索子组事项（不含正文）" clearable />
      <span class="scope-hint">仅摘要：标题 / 状态 / 负责人 / 截止</span>
    </div>

    <template v-if="loading && !items.length">
      <DewCard v-for="i in 3" :key="i" size="md" variant="flat"><DewSkeleton variant="text" :lines="2" /></DewCard>
    </template>
    <DewCard v-else-if="loadFailed" size="md" variant="flat">
      <p class="empty-text">汇总加载失败，请重试</p>
      <DewButton size="sm" :loading="loading" @click="load">重试</DewButton>
    </DewCard>
    <DewCard v-else-if="!items.length" size="md" variant="flat">
      <p class="empty-text">子组暂无可见事项</p>
    </DewCard>

    <template v-else>
      <DewCard v-for="it in items" :key="it.id" size="md" variant="flat" interactive class="sum-card"
               @click="onCardClick(it)">
        <div class="sum-row">
          <div class="sum-main">
            <div class="sum-title-line">
              <el-icon v-if="it.restricted" class="lock-icon" :size="13"><Lock /></el-icon>
              <span class="sum-title">{{ it.restricted ? '一项受限事项' : it.title }}</span>
            </div>
            <div class="sum-meta">
              <span>{{ it.group_name }}</span>
              <span v-if="!it.restricted && it.assignee_name">{{ it.assignee_name }} 负责</span>
              <span v-if="!it.restricted && it.due_at" :class="{ 'sum-overdue': it.overdue }">
                截止 {{ it.due_at }}{{ it.overdue ? '（已逾期）' : '' }}
              </span>
              <span v-if="!it.restricted">{{ it.last_activity_at }}</span>
            </div>
          </div>
          <DewTag v-if="!it.restricted" :type="ITEM_STATUS_TYPE[it.status] || 'neutral'"
                  size="sm" round>{{ ITEM_STATUS_LABELS[it.status] || it.status }}</DewTag>
        </div>
      </DewCard>
      <div v-if="total > pageSize" class="pager-row">
        <el-pagination background layout="prev, pager, next" :total="total" :page-size="pageSize"
                       :current-page="page" @current-change="(p) => { page = p; load() }" />
      </div>
    </template>
  </div>
</template>

<style scoped>
.filter-bar { display: flex; align-items: center; gap: 14px; margin-bottom: 14px; flex-wrap: wrap; }
.scope-hint { font-size: 12px; color: var(--dew-text-muted); }
.sum-card { margin-bottom: 10px; }
.sum-row { display: flex; align-items: center; gap: 12px; }
.sum-main { flex: 1; min-width: 0; }
.sum-title-line { display: flex; align-items: center; gap: 6px; }
.sum-title { font-size: 14px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.lock-icon { color: var(--dew-text-muted); flex: none; }
.sum-meta { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 4px; font-size: 12px; color: var(--dew-text-muted); }
.sum-overdue { color: var(--el-color-danger, #f56c6c); font-weight: 600; }
.pager-row { display: flex; justify-content: center; margin-top: 12px; }
.empty-text { margin: 4px 0 10px; font-size: 13px; color: var(--dew-text-muted); }
</style>
