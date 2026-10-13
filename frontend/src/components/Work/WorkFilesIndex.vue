<script setup>
// 「工作资料」附件索引（M4）：跨我的可见事项聚合 + 文件名检索（§12.3 受限检索，
// 服务端按访问权过滤）。索引不落盘下载：点击跳事项页（携带 link_id 上下文）。
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { DewCard, DewSkeleton, DewButton } from '@bme/dew-ui'
import { Search, Document } from '@element-plus/icons-vue'
import { workService } from '../../services/workService'
import { formatFileSize } from '../../utils/fileSize'

const router = useRouter()
const keyword = ref('')
const loading = ref(true)
const loadFailed = ref(false)
const files = ref([])
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
    const res = await workService.searchFiles(params)
    if (seq !== loadSeq) return      // 过期响应丢弃
    files.value = res.data?.files || []
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
onUnmounted(() => clearTimeout(debounce))
onMounted(load)

// 索引下载按事项附件关联判权：跳事项页下载（与整卡点击同目标）
function openItem(f) {
  router.push(`/work/items/${f.item_id}`)
}
</script>

<template>
  <div class="files-index">
    <div class="filter-bar">
      <el-input v-model="keyword" :prefix-icon="Search" style="width: 240px;"
                placeholder="按文件名搜索（仅你可见的事项）" clearable />
    </div>

    <template v-if="loading && !files.length">
      <DewCard v-for="i in 3" :key="i" size="md" variant="flat"><DewSkeleton variant="text" :lines="2" /></DewCard>
    </template>
    <DewCard v-else-if="loadFailed" size="md" variant="flat">
      <p class="empty-text">加载失败</p>
      <DewButton size="sm" @click="load">重试</DewButton>
    </DewCard>
    <DewCard v-else-if="!files.length" size="md" variant="flat">
      <p class="empty-text">暂无附件；事项里上传的交付与资料会汇总在这里</p>
    </DewCard>

    <template v-else>
      <DewCard v-for="f in files" :key="f.id" size="md" variant="flat" interactive class="file-card"
               @click="openItem(f)">
        <div class="file-row">
          <el-icon class="file-icon" :size="16"><Document /></el-icon>
          <div class="file-main">
            <div class="file-name">{{ f.display_name }}</div>
            <div class="file-meta">
              <span>{{ f.item_title }}</span>
              <span>{{ formatFileSize(f.size) }}</span>
              <span>{{ f.uploaded_by }} 上传</span>
              <span>{{ f.updated_at }}</span>
            </div>
          </div>
          <DewButton size="sm" @click.stop="openItem(f)">查看</DewButton>
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
.filter-bar { display: flex; gap: 10px; margin-bottom: 14px; }
.file-card { margin-bottom: 10px; }
.file-row { display: flex; align-items: center; gap: 10px; }
.file-icon { color: var(--dew-text-muted); flex: none; }
.file-main { flex: 1; min-width: 0; }
.file-name { font-size: 14.5px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.file-meta { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 4px; font-size: 12px; color: var(--dew-text-muted); }
.pager-row { display: flex; justify-content: center; margin-top: 12px; }
.empty-text { margin: 4px 0 10px; font-size: 13px; color: var(--dew-text-muted); }
</style>
