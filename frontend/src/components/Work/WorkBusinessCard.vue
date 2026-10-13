<script setup>
// 事项详情「关联对象」卡（X2 通用投影）：盲渲染适配器 fields 字典——组件不懂
// 任何业务语义。不可访问回占位（不泄露标题）；协调员∨作者可添加/移除关联。
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { DewCard, DewTag, DewButton } from '@bme/dew-ui'
import { Link } from '@element-plus/icons-vue'
import { workService } from '../../services/workService'

const props = defineProps({
  itemId: { type: Number, required: true },
  links: { type: Array, default: () => [] },
  canManage: { type: Boolean, default: false },   // 协调员∨作者
})
const emit = defineEmits(['changed'])

const addVisible = ref(false)
const types = ref([])
const typesLoading = ref(false)
const form = ref({ sourceType: '', sourceId: null })
const saving = ref(false)
const removing = ref(null)

async function openAdd() {
  addVisible.value = true
  form.value = { sourceType: '', sourceId: null }
  if (!types.value.length) {
    typesLoading.value = true
    try {
      const res = await workService.fetchObjectTypes()
      types.value = res.data?.types || []
    } finally { typesLoading.value = false }
  }
}

async function submitAdd() {
  if (!form.value.sourceType || !form.value.sourceId || saving.value) return
  saving.value = true
  try {
    const res = await workService.createLink(props.itemId, {
      source_type: form.value.sourceType,
      source_id: Number(form.value.sourceId),
    })
    ElMessage.success(res.message || '已关联')
    addVisible.value = false
    emit('changed')
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '关联失败（检查对象 ID）')
  } finally { saving.value = false }
}

async function removeLink(link) {
  if (removing.value) return
  removing.value = `${link.source_type}:${link.source_id}`
  try {
    await workService.removeLink(props.itemId, link.source_type, link.source_id)
    ElMessage.success('已移除关联')
    emit('changed')
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '移除失败')
  } finally { removing.value = null }
}

const fieldsOf = (link) => {
  const entries = Object.entries(link.fields || {}).filter(([k]) => k !== 'title')
  return entries
}
</script>

<template>
  <DewCard v-if="links.length || canManage" size="md" variant="flat" class="biz-card">
    <div class="biz-head">
      <el-icon :size="15"><Link /></el-icon>
      <span class="biz-title">关联对象（{{ links.length }}）</span>
      <span class="biz-hint">关联不改变原业务；内容按原业务权限显示</span>
      <div class="spacer" />
      <DewButton v-if="canManage" size="sm" @click="openAdd">添加关联</DewButton>
    </div>

    <div v-if="links.length" class="biz-list">
      <div v-for="l in links" :key="`${l.source_type}:${l.source_id}`" class="biz-row">
        <DewTag type="neutral" size="sm" round>{{ l.label }}</DewTag>
        <template v-if="l.accessible">
          <span class="biz-name">{{ l.fields?.title }}</span>
          <span v-for="[k, v] in fieldsOf(l)" :key="k" class="biz-field">
            {{ k }}：{{ v ?? '—' }}
          </span>
        </template>
        <span v-else class="biz-restricted">不可访问（无该业务查看权限）</span>
        <div class="spacer" />
        <DewButton v-if="canManage" text size="sm" :loading="removing === `${l.source_type}:${l.source_id}`"
                   @click="removeLink(l)">移除</DewButton>
      </div>
    </div>
    <p v-else class="biz-empty">暂无关联；可把课程/营期/工单挂到本事项作为工作上下文</p>

    <el-dialog v-model="addVisible" title="添加关联对象" width="420px" append-to-body>
      <el-form label-width="80px">
        <el-form-item label="类型">
          <el-select v-model="form.sourceType" :loading="typesLoading" style="width: 100%;"
                     placeholder="选择对象类型">
            <el-option v-for="t in types" :key="t.source_type" :label="t.label"
                       :value="t.source_type" />
          </el-select>
        </el-form-item>
        <el-form-item label="对象 ID">
          <el-input-number v-model="form.sourceId" :min="1" controls-position="right"
                           placeholder="业务对象编号" style="width: 160px;" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving"
                   :disabled="!form.sourceType || !form.sourceId" @click="submitAdd">
          关联
        </el-button>
      </template>
    </el-dialog>
  </DewCard>
</template>

<style scoped>
.biz-card { margin-top: 14px; }
.biz-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.biz-title { font-size: 14px; font-weight: 600; }
.biz-hint { font-size: 12px; color: var(--dew-text-muted); }
.spacer { flex: 1; }
.biz-list { margin-top: 8px; }
.biz-row { display: flex; align-items: center; gap: 10px; padding: 8px 0; flex-wrap: wrap;
           border-bottom: 1px dashed var(--dew-border); }
.biz-row:last-child { border-bottom: none; }
.biz-name { font-size: 13.5px; font-weight: 600; }
.biz-field { font-size: 12px; color: var(--dew-text-muted); }
.biz-restricted { font-size: 12.5px; color: var(--dew-text-muted); font-style: italic; }
.biz-empty { font-size: 13px; color: var(--dew-text-muted); padding: 6px 0; margin: 0; }
</style>
