<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Bell } from '@element-plus/icons-vue'
import api from '../../api'
const router = useRouter()
const items = ref([])
const unread = ref(0)
const failed = ref(false)
async function load() {
  try { const { data } = await api.get('/notifications'); items.value = data.items; unread.value = data.unread; failed.value = false }
  catch { failed.value = true }
}
async function open(item) {
  await api.post(`/notifications/${item.id}/read`)
  await load()
  if (item.source_type === 'work_item' && item.source_id) await router.push(`/work/items/${item.source_id}`)
}
onMounted(load)
</script>
<template>
  <el-popover trigger="click" width="340" @show="load">
    <template #reference><button class="notification-trigger" aria-label="工作通知"><Bell />{{ unread || '' }}</button></template>
    <p v-if="failed">通知暂时无法加载，请重试。</p>
    <p v-else-if="!items.length">暂无工作通知</p>
    <div v-else class="notification-list"><button v-for="item in items" :key="item.id" @click="open(item)"><strong>{{ item.title }}</strong><p>{{ item.content }}</p></button></div>
  </el-popover>
</template>
<style scoped>
.notification-trigger { display:flex; align-items:center; gap:4px; border:0; background:transparent; cursor:pointer; }
.notification-trigger svg { width:20px; height:20px; }
.notification-list { max-height:400px; overflow:auto; }
.notification-list button { display:block; width:100%; padding:10px; text-align:left; background:transparent; border:0; border-bottom:1px solid #eee; cursor:pointer; }
</style>
