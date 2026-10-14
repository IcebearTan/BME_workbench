import { createRouter, createWebHistory } from 'vue-router'
import { store } from '../store/index.js'
import { safeReturnPath, takeReturnPath } from '../auth/return-path.js'
import AccessView from '../views/AccessView.vue'
import WorkspacesView from '../views/WorkspacesView.vue'
import ManageView from '../views/ManageView.vue'

export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/work', component: () => import('../views/WorkShell.vue'), meta: { protected: true }, children: [
      { path: '', name: 'work', component: () => import('../views/WorkOverview.vue') },
      { path: 'items', component: () => import('../views/WorkItemsTable.vue') },
      { path: 'items/:id', name: 'work-item', component: () => import('../views/WorkItemView.vue') },
      { path: 'board', component: () => import('../components/Work/WorkBoard.vue') },
      { path: 'members', component: () => import('../views/WorkMembersView.vue') },
      { path: 'appointments', component: () => import('../views/AppointmentHistoryView.vue') },
      { path: 'organization', component: () => import('../views/OrganizationManageView.vue'), meta: { permission: 'governance:manage' } },
      { path: 'summary', component: () => import('../components/Work/WorkSummaryBoard.vue') },
      { path: 'files', component: () => import('../components/Work/WorkFilesIndex.vue') },
      { path: 'records', component: () => import('../components/Work/WorkRecordsIndex.vue') },
      { path: 'governance', component: () => import('../components/WorkGrantManage.vue') },
    ] },
    { path: '/', name: 'workspaces', component: WorkspacesView, meta: { protected: true, title: '我的工作空间' } },
    { path: '/manage', name: 'manage', component: ManageView, meta: { protected: true, permission: 'governance:view', title: '工作台管理' } },
    { path: '/login', name: 'login', component: AccessView, meta: { title: '登录' } },
    { path: '/access', name: 'access', component: AccessView, meta: { title: '访问资格' } },
    { path: '/unavailable', name: 'unavailable', component: AccessView, meta: { title: '身份服务' } },
    { path: '/forbidden', name: 'forbidden', component: AccessView, meta: { title: '访问权限' } },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

export function accessRoute(returnPath = '/') {
  const redirect = safeReturnPath(returnPath)
  switch (store.state.identityState) {
    case 'anonymous': return { name: 'login', query: { redirect } }
    case 'forbidden': return { name: 'access', query: { redirect } }
    case 'unavailable': return { name: 'unavailable', query: { redirect } }
    default: return null
  }
}

router.beforeEach(async (to) => {
  if (to.path === '/work' && typeof to.query.tab === 'string') {
    const tabs = { todo: '/work', group: '/work/items', board: '/work/board', summary: '/work/summary', files: '/work/files', records: '/work/records' }
    const query = { ...to.query }; delete query.tab
    return { path: tabs[to.query.tab] || '/work', query }
  }
  if (store.state.identityState === 'unknown' || to.meta.protected) await store.dispatch('refreshIdentity')
  if (to.meta.protected) {
    const redirect = accessRoute(to.fullPath)
    if (redirect) return redirect
    if (to.meta.permission && !store.state.permissions.includes(to.meta.permission)) return { name: 'forbidden' }
    if (to.path === '/') {
      const returnPath = takeReturnPath()
      if (returnPath !== '/') return returnPath
      if (import.meta.env.VITE_COLLAB_ENABLED === 'true') return '/work'
    }
  }
  if (to.name === 'login' && store.getters.authenticated && !to.query.error) return safeReturnPath(to.query.redirect)
})

router.afterEach((to) => { document.title = `${to.meta.title || '工作台'} · BME 内部工作台` })
