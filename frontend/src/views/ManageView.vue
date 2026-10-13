<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useStore } from 'vuex'
import { DewCard } from '@bme/dew-ui'
import { Lock } from '@element-plus/icons-vue'
import { api, apiError } from '../api/client.js'
import { accessRoute } from '../router/index.js'

const store = useStore()
const router = useRouter()
const summary = ref(null)
onMounted(async () => {
  try { summary.value = (await api.get('/admin/overview')).data }
  catch (error) {
    const failure = apiError(error)
    if (failure.status === 403 && failure.code === 'PERMISSION_DENIED') await router.replace('/forbidden')
    else {
      store.commit('identityFailure', failure)
      await router.replace(accessRoute('/manage') || '/unavailable')
    }
  }
})
</script>

<template>
  <section>
    <div class="page-heading"><div><span class="eyebrow">管理</span><h1>工作台管理</h1><p>管理权限在工作台内独立授予，训练营管理员身份不会自动获得这里的权限。</p></div></div>
    <DewCard v-if="!summary" variant="flat"><p role="status" class="muted">正在核验管理权限…</p></DewCard>
    <template v-else>
      <div class="summary-grid"><DewCard variant="flat"><span class="muted">已建立工作台身份</span><p class="stat-number">{{ summary.members }}</p></DewCard><DewCard variant="flat"><span class="muted">工作空间</span><p class="stat-number">{{ summary.workspaces }}</p></DewCard></div>
      <DewCard variant="flat" class="management-note"><Lock class="empty-icon" /><h2>管理授权已验证</h2><p>当前开放身份与权限基础。成员分配、工作空间配置与交接管理将在后续迁移中接入。</p><p class="muted">社团身份的授予与撤销继续由训练营平台管理。</p></DewCard>
    </template>
  </section>
</template>
