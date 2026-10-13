<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useStore } from 'vuex'
import { DewButton, DewCard } from '@bme/dew-ui'
import { ArrowRight, Connection, Lock, Warning } from '@element-plus/icons-vue'
import { api, apiError } from '../api/client.js'
import { safeReturnPath, rememberReturnPath } from '../auth/return-path.js'
import { accessRoute } from '../router/index.js'

const route = useRoute()
const router = useRouter()
const store = useStore()
const busy = ref(false)
const loadingProvider = ref(true)
const loginError = ref(null)
const callbackError = computed(() => typeof route.query.error === 'string' ? route.query.error : null)
const unavailable = computed(() => route.name === 'unavailable' || callbackError.value === 'IDENTITY_PROVIDER_UNAVAILABLE')
const denied = computed(() => route.name === 'access' || callbackError.value === 'ADMISSION_DENIED')
const permissionDenied = computed(() => route.name === 'forbidden')
const loginEnabled = computed(() => store.state.provider?.login_enabled === true)
const isLogin = computed(() => !unavailable.value && !denied.value && !permissionDenied.value)
const title = computed(() => unavailable.value ? '暂时无法核验身份' : denied.value ? '暂未获得工作台访问资格' : permissionDenied.value ? '你没有此管理权限' : '让协作，从这里开始')
const description = computed(() => unavailable.value
  ? '身份服务当前不可用，请稍后重试。服务恢复前，工作内容暂不展示；这不代表你的登录已退出或社团身份已被撤销。'
  : denied.value ? '工作台面向已开通访问资格的社团工作人员。请联系训练营平台的社团身份管理员核实你的身份状态。'
  : permissionDenied.value ? '工作台管理仅对获得管理授权的工作人员开放。如需权限，请联系工作台管理员。'
  : '使用训练营账号验证身份，以社团工作人员身份进入独立工作台。')

onMounted(async () => {
  await store.dispatch('loadProvider')
  loadingProvider.value = false
})

async function login() {
  if (busy.value || !loginEnabled.value) return
  busy.value = true
  loginError.value = null
  try {
    const { data } = await api.post('/auth/login')
    const target = new URL(data.authorization_url)
    if (!['https:', 'http:'].includes(target.protocol)) throw new Error('Invalid authorization URL')
    rememberReturnPath(route.query.redirect)
    window.location.assign(target.href)
  } catch (error) {
    loginError.value = apiError(error).code === 'IDENTITY_PROVIDER_UNAVAILABLE'
      ? '训练营身份接入当前不可用，请稍后重试。'
      : '暂时无法发起登录，请稍后重试。'
    busy.value = false
  }
}

async function retry() {
  busy.value = true
  await Promise.all([store.dispatch('refreshIdentity'), store.dispatch('loadProvider')])
  await router.replace(accessRoute(route.query.redirect) || safeReturnPath(route.query.redirect))
  busy.value = false
}
</script>

<template>
  <section class="access-page">
    <div class="access-intro"><span class="eyebrow">BME WORKBENCH</span><h1>专注每一份协作</h1><p>共同的身份，清晰的职责。<br />为社团工作人员准备的工作空间。</p></div>
    <DewCard variant="flat" class="access-card">
      <div class="state-icon"><component :is="unavailable ? Connection : denied || permissionDenied ? Lock : ArrowRight" /></div>
      <h2>{{ title }}</h2><p class="description">{{ description }}</p>
      <template v-if="isLogin">
        <div v-if="callbackError" class="notice notice-error" role="alert">本次身份验证未完成，请重新发起登录。</div>
        <div v-if="!loadingProvider && !loginEnabled" class="notice" role="status"><Warning /><div><strong>{{ store.state.provider ? '训练营身份接入尚未配置' : '暂时无法连接工作台服务' }}</strong><p>{{ store.state.provider ? '登录将在身份接入完成后开放。无需另行注册工作台账号。' : '请检查服务状态后重试，当前无法发起登录。' }}</p></div></div>
        <p v-if="loginError" class="inline-error" role="alert">{{ loginError }}</p>
        <DewButton block :active="loginEnabled" :disabled="!loginEnabled || loadingProvider" :loading="busy || loadingProvider" @click="login">使用训练营账号继续<ArrowRight class="button-icon" /></DewButton>
        <button v-if="!loadingProvider && !loginEnabled" type="button" class="text-button" :disabled="busy" @click="retry">重新检查连接</button>
        <p class="access-footnote">训练营负责账号与社团身份验证；工作台独立管理工作权限。</p>
      </template>
      <DewButton v-else-if="permissionDenied" @click="router.replace('/')">返回我的工作空间</DewButton>
      <DewButton v-else :loading="busy" @click="retry">重新核验身份</DewButton>
    </DewCard>
  </section>
</template>
