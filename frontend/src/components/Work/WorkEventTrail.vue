<script setup>
// 工作事件时间线（§6.2：「系统确认发生了什么」与讨论区分呈现）。
// 默认折叠，展开时分页加载；治理类事件由后端按可见范围过滤。
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { DewCard, DewButton } from '@bme/dew-ui'
import { workService, EVENT_LABELS } from '../../services/workService'

const props = defineProps({
  itemId: { type: Number, required: true },
})

const expanded = ref(false)
const loading = ref(false)
const events = ref([])
const total = ref(0)
const page = ref(1)

async function load() {
  loading.value = true
  try {
    const res = await workService.fetchEvents(props.itemId, {
      page: page.value, page_size: 30,
    })
    events.value = res.data?.events || []
    total.value = res.data?.total || 0
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '操作记录加载失败')
  } finally {
    loading.value = false
  }
}

async function toggle() {
  expanded.value = !expanded.value
  if (expanded.value && !events.value.length) await load()
}

onMounted(() => { /* 懒加载：展开时才取数 */ })
</script>

<template>
  <DewCard size="md" variant="flat" class="trail-card">
    <div class="trail-head" @click="toggle">
      <span class="trail-title">操作记录</span>
      <span class="trail-sub">谁在何时改变了状态、时限与访问范围</span>
      <DewButton type="ghost" size="sm" :loading="loading">
        {{ expanded ? '收起' : '展开' }}
      </DewButton>
    </div>
    <div v-if="expanded" class="trail-list">
      <div v-for="e in events" :key="e.seq" class="trail-row">
        <span class="trail-dot" />
        <div class="trail-body">
          <span class="trail-actor">{{ e.actor_name || '系统' }}</span>
          <span class="trail-action">{{ EVENT_LABELS[e.event_type] || e.event_type }}</span>
          <span v-if="e.reason" class="trail-reason">{{ e.reason }}</span>
          <span class="trail-time">{{ e.created_at }}</span>
        </div>
      </div>
      <p v-if="!events.length && !loading" class="trail-empty">暂无记录</p>
      <div v-if="total > 30" class="trail-pager">
        <el-pagination small background layout="prev, pager, next" :total="total" :page-size="30"
                       :current-page="page" @current-change="(p) => { page = p; load() }" />
      </div>
    </div>
  </DewCard>
</template>

<style scoped>
.trail-card { margin-top: 16px; }
.trail-head { display: flex; align-items: center; gap: 8px; cursor: pointer; }
.trail-title { font-size: 14px; font-weight: 600; }
.trail-sub { flex: 1; font-size: 12px; color: var(--dew-text-muted); }

.trail-list { margin-top: 12px; }
.trail-row { display: flex; gap: 10px; padding: 6px 0; }
.trail-dot {
  width: 7px; height: 7px; border-radius: 50%; margin-top: 7px; flex: none;
  background: var(--color-primary); opacity: 0.65;
}
.trail-body { flex: 1; font-size: 13px; line-height: 1.7; }
.trail-actor { font-weight: 600; margin-right: 6px; }
.trail-action { color: var(--dew-text); }
.trail-reason { margin-left: 6px; color: var(--dew-text-muted); }
.trail-time { float: right; font-size: 12px; color: var(--dew-text-muted); }
.trail-empty { font-size: 13px; color: var(--dew-text-muted); }
.trail-pager { display: flex; justify-content: center; margin-top: 8px; }

@media (max-width: 768px) {
  .trail-sub { display: none; }
}
</style>
