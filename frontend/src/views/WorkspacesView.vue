<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useStore } from 'vuex'
import { DewButton, DewCard } from '@bme/dew-ui'
import { OfficeBuilding, User, Check } from '@element-plus/icons-vue'
import { api, apiError } from '../api/client.js'
import { accessRoute } from '../router/index.js'

const store = useStore()
const router = useRouter()
const loading = ref(true)
const items = ref([])
const name = computed(() => store.state.actor?.display_name || '工作人员')

async function load() {
  loading.value = true
  try { items.value = (await api.get('/workspaces')).data.items || [] }
  catch (error) {
    store.commit('identityFailure', apiError(error))
    await router.replace(accessRoute('/') || '/unavailable')
  } finally { loading.value = false }
}
onMounted(load)
</script>

<template>
  <section class="workspace-page">
    <div class="page-heading"><div><span class="eyebrow">工作空间</span><h1>{{ name }}，欢迎回来</h1><p>从你的工作空间开始，查看团队与协作安排。</p></div><DewButton size="sm" type="ghost" :loading="loading" @click="load">刷新</DewButton></div>
    <div class="identity-strip"><User /><span>训练营账号</span><span class="identity-divider" /><Check /><span>社团身份有效</span><span class="identity-divider" /><span>{{ store.getters.canManage ? '已获工作台管理授权' : '工作权限由工作台独立管理' }}</span></div>
    <h2 class="section-title">我的工作空间</h2>
    <DewCard v-if="loading" variant="flat"><p role="status" class="muted">正在加载工作空间…</p></DewCard>
    <DewCard v-else-if="!items.length" variant="flat" class="empty-card"><OfficeBuilding class="empty-icon" /><h3>还没有加入工作空间</h3><p>你的身份已通过核验。工作空间分配将在协作功能接入后开放。</p><p class="muted">现阶段已完成登录与权限基础，已有工作事项仍请在原工作台处理。</p></DewCard>
    <div v-else class="workspace-grid"><DewCard v-for="item in items" :key="item.id" variant="flat"><OfficeBuilding class="workspace-icon" /><h3>{{ item.name }}</h3><p class="muted">{{ item.role === 'coordinator' ? '协调员' : '成员' }}</p><p class="muted">协作功能接入后开放</p></DewCard></div>
  </section>
</template>
