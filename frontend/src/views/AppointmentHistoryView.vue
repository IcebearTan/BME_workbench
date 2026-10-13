<script setup>
import { computed, ref, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useStore } from 'vuex'
import { DewCard, DewButton, DewSkeleton, DewTag } from '@bme/dew-ui'
import { api } from '../api/client'

const route = useRoute(), router = useRouter(), store = useStore()
const data = ref(null), loading = ref(false), error = ref('')
let requestNumber = 0
const userId = computed(() => route.query.user_id || store.state.actor?.subject)
const year = computed(() => route.query.year || '')
const groups = computed(() => {
  if (!data.value) return []
  const records = data.value.records || []
  const years = year.value ? [Number(year.value)] : data.value.years
  const result = years.map(y => ({ key: String(y), label: `${y} 年`, records: records.filter(r => r.years.includes(y)) })).filter(g => g.records.length)
  const undated = records.filter(r => !r.years.length)
  if (!year.value && undated.length) result.push({ key: 'unknown', label: '年份不详', records: undated })
  return result
})
const sourceLabel = r => ({ system: '系统记录', legacy: '既有记录', backfill: '历史补录' }[r.record_source] || '既有记录')
const eventLabel = e => e.kind === 'officer_edited' ? (e.detail?.mode === 'correction' ? '信息纠错' : '任职信息修改') : ({ officer_appointed: '登记任命', officer_ended: '登记卸任', officer_backfilled: '补录历史任职' }[e.kind] || '任职变更')
const fieldLabels = { title: '职位', title_id: '职位标识', department: '组别', group_id: '组别标识', term_start: '任期起', term_end: '任期止', scope_note: '任职范围', end_reason: '卸任原因', source_note: '资料来源', historical_year: '已知年份', org_slot_snapshot: '职位类别' }
const changes = e => Object.entries(e.detail?.changes || {}).filter(([key]) => fieldLabels[key] && !key.endsWith('_id')).map(([key, value]) => `${fieldLabels[key]}：${value.from || '不详'} → ${value.to || '不详'}`).join('；')
function selectPerson(value) {
  router.replace({ query: { user_id: String(value) } })
}
function selectYear(value) {
  const query = { ...route.query }
  if (value) query.year = String(value)
  else delete query.year
  router.replace({ query })
}
async function load() {
  const number = ++requestNumber
  loading.value = true
  error.value = ''
  data.value = null
  try {
    const response = await api.get('/appointments/history', { params: { user_id: userId.value, ...(year.value ? { year: year.value } : {}) } })
    if (number === requestNumber) data.value = response.data.data
  } catch (e) {
    if (number === requestNumber) error.value = e.response?.data?.error?.message || '任职履历加载失败，请重试'
  } finally {
    if (number === requestNumber) loading.value = false
  }
}
watch(() => route.fullPath, load)
onMounted(load)
</script>

<template>
  <div class="appointment-history">
    <div class="history-heading">
      <div><h1>任职履历</h1><p>按年份查看职位、任期和变更记录。跨年任职会出现在覆盖的每个年份。</p></div>
      <DewButton type="ghost" size="sm" :loading="loading" @click="load">刷新</DewButton>
    </div>
    <div v-if="error" role="alert" class="notice notice-error">{{ error }}</div>
    <DewSkeleton v-else-if="loading" :rows="5" />
    <template v-else-if="data">
      <div class="history-filters">
        <el-select v-if="data.can_select_person" :model-value="Number(userId)" aria-label="选择人员" filterable @change="selectPerson">
          <el-option v-for="person in data.people" :key="person.id" :label="`${person.name} · #${person.id}`" :value="person.id" />
        </el-select>
        <strong v-else>{{ data.username }}</strong>
        <el-select :model-value="year" aria-label="选择年份" placeholder="全部年份" @change="selectYear">
          <el-option label="全部年份" value="" />
          <el-option v-for="y in data.years" :key="y" :label="`${y} 年`" :value="String(y)" />
        </el-select>
      </div>
      <p class="history-note">这里只展示已登记的事实。历史补录和既有记录可能缺少精确日期或早期操作日志。</p>
      <p v-if="year && data.undated_count" class="history-note">另有 {{ data.undated_count }} 条年份不详的任职，可在“全部年份”中查看。</p>
      <el-empty v-if="!groups.length" description="该年份暂无已登记的任职记录" />
      <section v-for="group in groups" :key="group.key" class="history-year" :aria-label="group.label">
        <h2>{{ group.label }}</h2>
        <DewCard v-for="record in group.records" :key="record.id" no-hover variant="flat" class="history-record">
          <div class="record-heading"><h3>{{ record.title }}</h3><DewTag size="sm" :type="record.status === 'active' ? 'success' : 'info'">{{ record.display_status === 'scheduled' ? '待生效' : record.status === 'active' ? '在任' : '已结束' }}</DewTag><DewTag size="sm" type="info">{{ sourceLabel(record) }}</DewTag></div>
          <p>{{ record.department || '社团职务' }}</p>
          <p class="term">{{ record.term_start || '开始日期不详' }} — {{ record.term_end || (record.status === 'active' ? '至今' : '结束日期不详') }}</p>
          <p v-if="record.historical_year && record.date_precision === 'year'">仅确认 {{ record.historical_year }} 年任职，具体日期不详。</p>
          <p v-if="record.scope_note">任职范围：{{ record.scope_note }}</p>
          <p v-if="record.end_reason">结束原因：{{ record.end_reason }}</p>
          <p v-if="record.source_note" class="history-note">资料来源：{{ record.source_note }}</p>
          <el-collapse>
            <el-collapse-item :title="`变更记录（${record.events.length}）`" :name="String(record.id)">
              <p v-if="!record.events.length" class="history-note">没有可用的早期操作日志；任期日期以已登记信息为准。</p>
              <ol v-else class="history-events"><li v-for="event in record.events" :key="event.id"><strong>{{ eventLabel(event) }}</strong><time>{{ event.occurred_at?.replace('T', ' ') || '操作时间不详' }}<span v-if="event.operator_name"> · {{ event.operator_name }}</span></time><p v-if="event.detail?.reason">{{ event.detail.reason }}</p><p v-if="changes(event)">{{ changes(event) }}</p></li></ol>
            </el-collapse-item>
          </el-collapse>
        </DewCard>
      </section>
    </template>
  </div>
</template>

<style scoped>
.appointment-history { max-width: 960px; margin: 0 auto; padding: 24px; color: var(--color-text); }
.history-heading, .record-heading, .history-filters { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.history-heading { justify-content: space-between; margin-bottom: 20px; }
h1 { margin: 0; font-size: 24px; } h2 { font-size: 20px; margin: 28px 0 12px; } h3 { font-size: 17px; margin: 0; }
p { line-height: 1.7; margin: 8px 0; }
.history-filters .el-select { width: 240px; max-width: 100%; }
.history-note, time { color: var(--color-text-secondary); font-size: 13px; }
.history-record { margin-bottom: 14px; }
.term { font-variant-numeric: tabular-nums; }
.history-events { padding-left: 22px; } .history-events li { margin: 10px 0; } time { display: block; margin-top: 4px; }
@media (max-width: 600px) { .appointment-history { padding: 16px; } .history-filters .el-select { width: 100%; } }
</style>
