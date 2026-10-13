<script setup>
// 事项附件区（M4）：上传（类型白名单前端提示）/版本历史/鉴权下载（fetch-blob）。
// 文件属于事项：人员卸任后文件仍保留（§9.1）；新版本不覆盖旧版本（B05）。
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { DewCard, DewDialog, DewButton } from '@bme/dew-ui'
import { Paperclip, Upload, Document } from '@element-plus/icons-vue'
import { workService } from '../../services/workService'
import { formatFileSize } from '../../utils/fileSize'

const props = defineProps({
  itemId: { type: Number, required: true },
  files: { type: Array, default: () => [] },
  canUpload: { type: Boolean, default: false },
})
const emit = defineEmits(['changed'])

const ALLOW_HINT = 'pdf / 图片 / txt / md / docx / xlsx / pptx，单文件 ≤25MB'
const uploading = ref(false)
const versionsVisible = ref(false)
const versionsLoading = ref(false)
const versions = ref([])
const versionsFileName = ref('')
const downloadingId = ref(null)

function triggerUpload(fileId = null) {
  const input = document.createElement('input')
  input.type = 'file'
  input.onchange = async () => {
    const file = input.files?.[0]
    if (!file) return
    uploading.value = true
    try {
      const res = await workService.uploadFile(props.itemId, file, fileId)
      ElMessage.success(fileId ? '已上传新版本' : '附件已上传')
      emit('changed')
    } catch (e) {
      const code = e.response?.status
      ElMessage.error(code === 413 ? `超出限制（${ALLOW_HINT}或事项配额）`
        : code === 415 ? '类型不允许或内容与扩展名不符'
        : (e.response?.data?.message || '上传失败'))
    } finally {
      uploading.value = false
    }
  }
  input.click()
}

async function openVersions(file) {
  versionsFileName.value = file.display_name
  versionsVisible.value = true
  versionsLoading.value = true
  try {
    const res = await workService.fetchFileVersions(file.id)
    versions.value = res.data?.versions || []
  } catch {
    versions.value = []
  } finally {
    versionsLoading.value = false
  }
}

async function download(file) {
  if (!file.link_id || downloadingId.value) return
  downloadingId.value = file.id
  try {
    await workService.downloadFile(file.id, file.link_id, file.display_name)
  } catch (e) {
    ElMessage.error(e.response?.status === 404 ? '文件不可访问或已被移除'
      : '下载失败，请重试')
  } finally {
    downloadingId.value = null
  }
}

const rows = computed(() => props.files || [])
</script>

<template>
  <DewCard size="md" variant="flat" class="files-card">
    <div class="files-head">
      <el-icon :size="15"><Paperclip /></el-icon>
      <span class="files-title">附件（{{ rows.length }}）</span>
      <span class="files-hint">{{ ALLOW_HINT }}</span>
      <div class="spacer" />
      <DewButton v-if="canUpload" size="sm" :loading="uploading" @click="triggerUpload()">
        <el-icon :size="13"><Upload /></el-icon>
        上传附件
      </DewButton>
    </div>

    <div v-if="rows.length" class="files-list">
      <div v-for="f in rows" :key="f.id" class="file-row">
        <el-icon class="file-icon" :size="16"><Document /></el-icon>
        <span class="file-name" :title="f.display_name">{{ f.display_name }}</span>
        <span v-if="f.current_version" class="file-meta">
          v{{ f.current_version.version_no }} · {{ formatFileSize(f.current_version.size) }}
          · {{ f.current_version.created_at }}
        </span>
        <div class="spacer" />
        <DewButton type="ghost" size="sm" @click="openVersions(f)">版本</DewButton>
        <DewButton v-if="canUpload" type="ghost" size="sm" @click="triggerUpload(f.id)">传新版本</DewButton>
        <DewButton type="ghost" size="sm" active :loading="downloadingId === f.id"
                   :disabled="!f.link_id" @click="download(f)">下载</DewButton>
      </div>
    </div>
    <p v-else class="files-empty">暂无附件；需要交付文件时从右上角上传</p>

    <DewDialog v-model="versionsVisible" :title="`版本历史 - ${versionsFileName}`" :width="480">
      <el-table v-loading="versionsLoading" :data="versions" size="small" style="width: 100%;">
        <el-table-column prop="version_no" label="版本" width="70">
          <template #default="{ row }">v{{ row.version_no }}</template>
        </el-table-column>
        <el-table-column label="大小" width="100">
          <template #default="{ row }">{{ formatFileSize(row.size) }}</template>
        </el-table-column>
        <el-table-column label="校验" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="row.format_check === 'passed' ? 'success' : 'danger'">
              {{ row.format_check === 'passed' ? '通过' : '拒绝' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="上传时间" min-width="120" />
      </el-table>
      <p class="versions-note">版本不可覆盖：已提交的交付固定引用当时的版本</p>
    </DewDialog>
  </DewCard>
</template>

<style scoped>
.files-card { margin-top: 14px; }
.files-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.files-title { font-size: 14px; font-weight: 600; }
.files-hint { font-size: 12px; color: var(--dew-text-muted); }
.spacer { flex: 1; }

.files-list { margin-top: 8px; }
.file-row { display: flex; align-items: center; gap: 8px; padding: 8px 0; border-bottom: 1px dashed var(--el-border-color-lighter); }
.file-row:last-child { border-bottom: none; }
.file-icon { color: var(--dew-text-muted); flex: none; }
.file-name { font-size: 13.5px; font-weight: 500; max-width: 40%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.file-meta { font-size: 12px; color: var(--dew-text-muted); font-variant-numeric: tabular-nums; }
.files-empty { font-size: 13px; color: var(--dew-text-muted); padding: 8px 0; }

.versions-note { margin: 10px 0 0; font-size: 12px; color: var(--dew-text-muted); }

/* 窄屏：文件名整行 + 操作按钮换行排布（DewButton sm 较宽，防 375px 溢出） */
@media (max-width: 768px) {
  .file-row { flex-wrap: wrap; }
  .file-name { max-width: 100%; }
}
</style>
