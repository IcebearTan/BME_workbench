<script setup>
import { computed, ref, watch } from 'vue'
import { useStore } from 'vuex'
import { useRoute, useRouter } from 'vue-router'
import { Briefcase, Grid, Setting, Menu, Close, SwitchButton } from '@element-plus/icons-vue'
import { DewButton } from '@bme/dew-ui'

const store = useStore()
const route = useRoute()
const router = useRouter()
const drawerOpen = ref(false)
const logoutBusy = ref(false)
const logoutError = ref(false)
const authenticated = computed(() => store.getters.authenticated)
const canManage = computed(() => store.getters.canManage)
watch(() => route.fullPath, () => { drawerOpen.value = false; logoutError.value = false })

async function logout() {
  logoutBusy.value = true
  logoutError.value = false
  if (await store.dispatch('logout')) await router.replace({ name: 'login' })
  else logoutError.value = true
  logoutBusy.value = false
}
</script>

<template>
  <RouterView v-if="route.path === '/work' || route.path.startsWith('/work/')" />
  <div v-else class="work-surface">
    <a class="skip-link" href="#main-content">跳到主要内容</a>
    <header class="app-header">
      <button v-if="authenticated" type="button" class="icon-button mobile-menu" :aria-expanded="drawerOpen" aria-controls="work-nav" aria-label="切换导航" @click="drawerOpen = !drawerOpen">
        <component :is="drawerOpen ? Close : Menu" />
      </button>
      <RouterLink to="/" class="brand" aria-label="BME 内部工作台首页"><Briefcase /><span>BME <strong>内部工作台</strong></span></RouterLink>
      <div class="header-spacer" />
      <span v-if="store.state.actor" class="account-name">{{ store.state.actor.display_name }}</span>
      <DewButton v-if="store.state.csrfToken" size="sm" type="ghost" :loading="logoutBusy" aria-label="退出工作台" @click="logout"><SwitchButton class="button-icon" /><span class="logout-label">退出</span></DewButton>
      <span v-else class="header-label">社团内部协作</span>
    </header>
    <div v-if="logoutError" role="alert" class="notice notice-error">退出未完成，请检查连接后重试。当前登录状态仍然保留。</div>
    <div class="app-body" :class="{ 'has-sidebar': authenticated }">
      <button v-if="authenticated && drawerOpen" type="button" class="nav-backdrop" aria-label="关闭导航" @click="drawerOpen = false" />
      <aside v-if="authenticated" id="work-nav" class="sidebar" :class="{ 'is-open': drawerOpen }">
        <div class="nav-label">工作台</div>
        <nav aria-label="工作台导航">
          <RouterLink to="/" class="nav-item" exact-active-class="is-active"><Grid /><span>我的工作空间</span></RouterLink>
          <RouterLink v-if="canManage" to="/manage" class="nav-item" active-class="is-active"><Setting /><span>工作台管理</span></RouterLink>
        </nav>
        <div class="sidebar-footer"><span class="status-dot" />训练营身份已验证</div>
      </aside>
      <main id="main-content" class="main-content" tabindex="-1"><RouterView /></main>
    </div>
  </div>
</template>
