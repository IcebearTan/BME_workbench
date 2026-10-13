<script setup>
// 「工作记录」检索（M5）：我的可见事项全史（含已完结）+ 关键词检索。
// 时间线/操作记录在事项详情页；此处是跨事项的历史入口（§6.1 工作记录）。
// 失败态与 WorkFilesIndex 同款（失败不伪装成「没有记录」）。
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { DewCard, DewTag, DewSkeleton, DewButton } from '@bme/dew-ui'
import { Search } from '@element-plus/icons-vue'
import { workService, ITEM_STATUS_LABELS, ITEM_STATUS_TYPE } from '../../services/workService'

const router = useRouter()
const keyword = ref('')
const scopeMine = ref(false)
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
    if (scopeMine.value) params.mine = 1
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

let debounce = null
watch(keyword, () => {
  clearTimeout(debounce)
  debounce = setTimeout(() => { page.value = 1; load() }, 400)
})
watch(scopeMine, () => { page.value = 1; load() })
onUnmounted(() => clearTimeout(debounce))
onMounted(load)
</script>

<template>
  <div class="records-index">
    <div class="filter-bar">
      <el-input v-model="keyword" :prefix-icon="Search" style="width: 240px;"
                placeholder="检索标题 / 正文（含已完结）" clearable />
      <el-checkbox v-model="scopeMine">只看我发起或参与的</el-checkbox>
    </div>

    <template v-if="loading && !items.length">
      <DewCard v-for="i in 3" :key="i" size="md" variant="flat"><DewSkeleton variant="text" :lines="2" /></DewCard>
    </template>
    <DewCard v-else-if="loadFailed" size="md" variant="flat">
      <p class="empty-text">记录加载失败，请重试</p>
      <DewButton size="sm" :loading="loading" @click="load">重试</DewButton>
    </DewCard>
    <DewCard v-else-if="!items.length" size="md" variant="flat">
      <p class="empty-text">没有匹配的工作记录</p>
    </DewCard>

    <template v-else>
      <DewCard v-for="it in items" :key="it.id" size="md" variant="flat" interactive class="record-card"
               @click="router.push(`/work/items/${it.id}`)">
        <div class="record-row">
          <div class="record-main">
            <div class="record-title">{{ it.title }}</div>
            <div class="record-meta">
              <span>{{ it.group_name }}</span>
              <span>{{ it.created_at }}</span>
              <span>回复 {{ it.reply_count }}</span>
            </div>
          </div>
          <DewTag :type="ITEM_STATUS_TYPE[it.status] || 'neutral'" size="sm" round>
            {{ ITEM_STATUS_LABELS[it.status] || it.status }}
          </DewTag>
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
.record-card { margin-bottom: 10px; }
.record-row { display: flex; align-items: center; gap: 12px; }
.record-main { flex: 1; min-width: 0; }
.record-title { font-size: 14.5px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.record-meta { display: flex; gap: 10px; margin-top: 4px; font-size: 12px; color: var(--dew-text-muted); }
.pager-row { display: flex; justify-content: center; margin-top: 12px; }
.empty-text { margin: 4px 0 10px; font-size: 13px; color: var(--dew-text-muted); }
</style>
