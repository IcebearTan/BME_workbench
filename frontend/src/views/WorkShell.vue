<script setup>
// 内部工作台应用外壳（工作台 III）：唯一 chrome 持有者——顶栏（返回平台/上下文/铃铛）
// + 侧栏（工作区切换器 + 导航）+ 内容区（router-view 子视图）。
// 外壳持有路由级数据（资格探测 + 待办摘要轮询），子视图只读单例（useWorkAccess/useWorkData）。
// flat 工作面：素色底、无极光无玻璃（work-surface.css），展示性由内容承担。
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useStore } from 'vuex'
import { DewCard, DewTag, DewSkeleton, DewButton } from '@bme/dew-ui'
import { ArrowLeft, Fold, Briefcase, Odometer, ChatLineSquare, DataBoard,
         OfficeBuilding, Folder, Clock, User } from '@element-plus/icons-vue'
import NotificationBell from '../components/Notification/NotificationBell.vue'
import '../styles/collaboration.css'
import { useWorkAccess } from '../composables/useWorkAccess'
import { useWorkData } from '../composables/useWorkData'

const store = useStore()
const route = useRoute()
const router = useRouter()
const isDarkMode = computed(() => store.getters.isDarkMode)

// ── 资格与摘要（外壳单点持有；探测失败/无资格在内容区出态，不渲染侧栏） ──
const { me, hasAccess, isGovernance, detecting, detectFailed, detect } = useWorkAccess()
const { todoCounts, refreshSummary, startSummaryPolling, stopSummaryPolling } = useWorkData()
const loading = computed(() => detecting.value && !me.value && !detectFailed.value)
const isAppointmentView = computed(() => route.path === '/work/appointments')
const load = async () => {
  await detect(true)
  if (hasAccess.value) {
    await refreshSummary().catch(() => {})
    startSummaryPolling()
  }
}

// 徽标口径 = 摘要五桶之和（待回复/待接手/待验收/即将到期/已逾期）
const todoBadgeTotal = computed(() =>
  (todoCounts.value.pending_responses || 0)
  + (todoCounts.value.pending_transfers || 0)
  + (todoCounts.value.to_review || 0)
  + (todoCounts.value.due_soon || 0)
  + (todoCounts.value.overdue || 0))

const hasSubtree = computed(() =>
  (me.value?.workspaces || []).some(w => w.subtree))

// ── 侧栏导航（URL 即导航；子组汇总仅 subtree 授权者渲染，路由常驻） ──
const navItems = computed(() => {
  if (isAppointmentView.value && !hasAccess.value) return [{ to: '/work/appointments', label: '任职履历', icon: Clock }]
  const items = [
    { to: '/work', label: '概览', icon: Odometer, badge: todoBadgeTotal.value || null },
    { to: '/work/items', label: '小组事项', icon: ChatLineSquare },
    { to: '/work/board', label: '看板', icon: DataBoard },
    { to: '/work/members', label: '成员', icon: User },
    { to: '/work/appointments', label: '任职履历', icon: Clock },
  ]
  if (hasSubtree.value) items.push({ to: '/work/summary', label: '子组汇总', icon: OfficeBuilding })
  items.push(
    { to: '/work/files', label: '工作资料', icon: Folder },
    { to: '/work/records', label: '工作记录', icon: Clock })
  return items
})
// 路径匹配：概览严格等于 /work；其余前缀匹配（/work/items/123 高亮「小组事项」）
function isActive(item) {
  if (item.to === '/work') return route.path === '/work'
  return route.path === item.to || route.path.startsWith(item.to + '/')
}
const viewLabel = computed(() => {
  if (route.name === 'work-item') return '事项详情'
  return navItems.value.find(isActive)?.label || ''
})

// ── 工作区切换器：写回 ?ws=（小组事项/看板视图消费），多区时才渲染 ──
const workspaces = computed(() => me.value?.workspaces || [])
const wsId = ref(null)
function syncWsFromQuery() {
  const ws = Number(route.query.ws) || null
  wsId.value = workspaces.value.some(w => w.id === ws) ? ws : null
}
watch(() => route.query.ws, syncWsFromQuery)
watch(workspaces, syncWsFromQuery, { immediate: true })
watch(wsId, (v) => {
  const query = { ...route.query }
  if (v) query.ws = String(v)
  else delete query.ws
  if (String(route.query.ws || '') !== (v ? String(v) : '')) {
    router.replace({ query })
  }
})

// ── 移动端：侧栏收抽屉（顶栏汉堡开关，导航点击即收起） ──
const isMobile = ref(window.innerWidth <= 768)
const drawerOpen = ref(false)
const checkScreenSize = () => {
  isMobile.value = window.innerWidth <= 768
  if (!isMobile.value) drawerOpen.value = false
}
onMounted(() => {
  window.addEventListener('resize', checkScreenSize)
  load()
})
onUnmounted(() => {
  window.removeEventListener('resize', checkScreenSize)
  stopSummaryPolling()
})

// 治理提示分流：管理端登录仅超管放行（isStaff 只认 super_admin），治理授权人员走超管代办
const isSuperAdmin = computed(() => store.state.permissions.includes('governance:manage'))
const backToPlatform = () => window.location.assign(import.meta.env.VITE_TRAINING_URL || '/')
</script>

<template>
  <div :class="['work-shell work-surface', { 'theme-dark': isDarkMode, 'theme-light': !isDarkMode }]">
    <!-- 顶栏：素色底 + 下边框（返回平台 | 上下文 | 铃铛） -->
    <header class="ws-topbar">
      <el-icon v-if="isMobile" class="ws-icon-btn" @click="drawerOpen = !drawerOpen"><Fold /></el-icon>
      <button type="button" class="ws-back" @click="backToPlatform">
        <el-icon :size="14"><ArrowLeft /></el-icon>
        <span>返回平台</span>
      </button>
      <div class="ws-crumb">
        <span class="ws-crumb-root">内部工作台</span>
        <template v-if="viewLabel">
          <span class="ws-crumb-sep">/</span>
          <span class="ws-crumb-view">{{ viewLabel }}</span>
        </template>
        <DewTag v-if="isGovernance" type="info" size="sm" round>治理</DewTag>
      </div>
      <div class="ws-topbar-spacer" />
      <NotificationBell />
      <DewButton type="ghost" size="sm" @click="async () => { if (await store.dispatch('logout')) { await router.replace('/login') } }">退出</DewButton>
    </header>

    <div class="ws-body">
      <!-- 侧栏：工作区切换器 + 导航（无资格不渲染） -->
      <aside v-if="hasAccess || isAppointmentView" :class="['ws-side', { 'ws-side--open': isMobile && drawerOpen }]">
        <div v-if="workspaces.length > 1" class="ws-ws-picker">
          <el-select v-model="wsId" placeholder="全部工作区" clearable size="default">
            <el-option v-for="w in workspaces" :key="w.id" :label="w.group_name" :value="w.id" />
          </el-select>
        </div>

        <nav class="ws-nav">
          <router-link v-for="item in navItems" :key="item.to" :to="item.to"
                       class="ws-nav-item" :class="{ 'ws-nav-item--active': isActive(item) }"
                       @click="drawerOpen = false">
            <el-icon :size="15" class="ws-nav-icon"><component :is="item.icon" /></el-icon>
            <span class="ws-nav-label">{{ item.label }}</span>
            <span v-if="item.badge" class="ws-nav-badge ws-num">{{ item.badge > 99 ? '99+' : item.badge }}</span>
          </router-link>
        </nav>

        <div v-if="isGovernance" class="ws-side-foot">
          <router-link to="/work/governance">打开工作台管理</router-link>
        </div>
      </aside>
      <div v-if="isMobile && drawerOpen" class="ws-backdrop" @click="drawerOpen = false" />

      <!-- 内容区：门禁三段式在外壳，子视图只在有资格时挂载 -->
      <main class="ws-main">
        <div class="ws-content">
          <template v-if="loading && !isAppointmentView">
            <DewSkeleton variant="rect" :height="24" :width="180" class="sk-block" />
            <DewCard v-for="i in 3" :key="i" size="md" class="sk-block">
              <DewSkeleton variant="text" :lines="2" />
            </DewCard>
          </template>

          <DewCard v-else-if="detectFailed && !isAppointmentView" size="md" class="state-card">
            <p class="state-text">工作台信息加载失败，请稍后重试</p>
            <DewButton size="sm" @click="load">重试</DewButton>
          </DewCard>

          <!-- 无资格空态：面向学员的友好说明（入口卡本就不可见，多为直达 URL） -->
          <DewCard v-else-if="!hasAccess && !isAppointmentView" size="md" class="state-card">
            <div class="empty-icon"><el-icon><Briefcase /></el-icon></div>
            <h3 class="state-title">内部工作台</h3>
            <p class="state-text">
              这里是社团工作人员的内部协作区（话题讨论、任务跟进与工作留痕），
              面向已开通权限的干事与组内工作人员。如你认为自己需要访问，请联系平台负责人开通。
            </p>
            <DewButton size="sm" @click="router.push('/work/members')">查看社团组织架构</DewButton>
            <DewButton size="sm" type="ghost" @click="router.push('/work/appointments')">查看我的任职履历</DewButton>
          </DewCard>

          <router-view v-else />
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped>
.work-shell { min-height: 100vh; display: flex; flex-direction: column; }

/* ── 顶栏 ── */
.ws-topbar {
  position: sticky; top: 0; z-index: 60;
  display: flex; align-items: center; gap: 14px;
  height: 52px; padding: 0 20px;
  background: var(--ws-topbar);
  border-bottom: 1px solid var(--ws-border);
}
.ws-icon-btn { font-size: 20px; cursor: pointer; color: var(--dew-text-muted); }
.ws-back {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 5px 10px; border: none; border-radius: 8px;
  font-size: 13px; color: var(--dew-text-muted); font-family: inherit;
  background: transparent; cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease;
}
.ws-back:hover { background: var(--ws-hover); color: var(--dew-text); }
.ws-crumb { display: flex; align-items: center; gap: 8px; min-width: 0; }
.ws-crumb-root { font-size: 14px; font-weight: 600; color: var(--dew-text-heading); }
.ws-crumb-sep { color: var(--dew-text-faint); }
.ws-crumb-view { font-size: 13px; color: var(--dew-text-muted); }
.ws-topbar-spacer { flex: 1; }

/* ── 侧栏 ── */
.ws-body { flex: 1; display: flex; min-height: 0; }
.ws-side {
  width: 228px; flex: none;
  display: flex; flex-direction: column;
  position: sticky; top: 52px;
  height: calc(100vh - 52px);
  overflow-y: auto;
  background: var(--ws-side);
  border-right: 1px solid var(--ws-border);
  padding: 16px 12px;
}
.ws-ws-picker { margin-bottom: 14px; }
.ws-ws-picker :deep(.el-select) { width: 100%; }

.ws-nav { display: flex; flex-direction: column; gap: 2px; }
.ws-nav-item {
  display: flex; align-items: center; gap: 9px;
  padding: 8px 10px; border-radius: 8px;
  font-size: 13.5px; color: var(--dew-text-muted); text-decoration: none;
  transition: background 0.2s ease, color 0.2s ease;
}
.ws-nav-item:hover { background: var(--ws-hover); color: var(--dew-text); }
.ws-nav-item--active {
  background: var(--ws-active);
  color: var(--dew-text-heading); font-weight: 600;
}
.ws-nav-icon { flex: none; }
.ws-nav-label { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ws-nav-badge {
  flex: none; min-width: 18px; padding: 1px 5px; border-radius: 9px;
  font-size: 11px; font-weight: 600; text-align: center;
  color: #fff; background: var(--el-color-danger, #f56c6c);
}

.ws-side-foot { margin-top: auto; padding-top: 14px; border-top: 1px solid var(--ws-border); }
.ws-side-foot p { margin: 0; font-size: 11.5px; line-height: 1.6; color: var(--dew-text-faint); }

/* ── 内容区 ── */
.ws-main { flex: 1; min-width: 0; padding: 20px 24px 48px; }

.sk-block { margin-bottom: 14px; }
.state-card { max-width: 560px; margin: 40px auto 0; text-align: center; }
.empty-icon {
  width: 48px; height: 48px; margin: 0 auto 12px; border-radius: 14px;
  display: flex; align-items: center; justify-content: center; font-size: 24px;
  background: color-mix(in srgb, var(--color-primary) 10%, transparent);
  color: var(--color-primary);
}
.state-title { margin: 0 0 8px; font-size: 17px; font-weight: 600; }
.state-text { margin: 0 0 12px; font-size: 13px; line-height: 1.7; color: var(--dew-text-muted); }

.ws-backdrop { position: fixed; inset: 52px 0 0 0; z-index: 70; background: rgba(0, 0, 0, 0.35); }

/* ── 移动端：侧栏收抽屉、内容全宽 ── */
@media (max-width: 768px) {
  .ws-topbar { padding: 0 14px; gap: 10px; }
  .ws-crumb-root { font-size: 13.5px; }
  .ws-side {
    position: fixed; left: 0; top: 52px; bottom: 0; height: auto; z-index: 80;
    width: 248px;
    transform: translateX(-100%);
    transition: transform 0.25s ease;
    box-shadow: none;
  }
  .ws-side--open { transform: none; box-shadow: 8px 0 24px rgba(0, 0, 0, 0.18); }
  .ws-main { padding: 14px 14px 32px; }
}
</style>
