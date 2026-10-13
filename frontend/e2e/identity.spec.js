import { test, expect } from '@playwright/test'

async function mockApi(page, options = {}) {
  const state = { authenticated: true, configured: true, permissions: [], meError: null, workspaceError: null, logoutError: null, ...options }
  const requests = []
  const fail = (route, status, code) => route.fulfill({ status, json: { error: { code, message: code } } })
  await page.route((url) => url.pathname.startsWith('/api/'), async (route) => {
    const request = route.request()
    const path = new URL(request.url()).pathname
    requests.push({ path, method: request.method(), headers: request.headers() })
    if (path === '/api/auth/status') return route.fulfill({ json: { configured: state.configured, login_enabled: state.configured, provider: 'training-platform', message: '训练营身份接入尚未配置' } })
    if (path === '/api/auth/me') {
      if (state.meError) return fail(route, ...state.meError)
      if (!state.authenticated) return fail(route, 401, 'SESSION_REQUIRED')
      return route.fulfill({ json: { actor: { id: 'local-1', display_name: '小林', issuer: 'training-platform', subject: 'account-1', person_id: 'person-1' }, admission: { community_active: true }, permissions: state.permissions, csrf_token: 'test-csrf-token' } })
    }
    if (path === '/api/auth/login') {
      state.authenticated = true
      return route.fulfill({ json: { authorization_url: 'http://127.0.0.1:18083/' } })
    }
    if (path === '/api/auth/logout') {
      if (state.logoutError) return fail(route, ...state.logoutError)
      state.authenticated = false
      return route.fulfill({ status: 204 })
    }
    if (path === '/api/workspaces') {
      if (state.workspaceError) return fail(route, ...state.workspaceError)
      return route.fulfill({ json: { items: [] } })
    }
    if (path === '/api/admin/overview') {
      if (!state.permissions.includes('governance:view')) return fail(route, 403, 'PERMISSION_DENIED')
      return route.fulfill({ json: { members: 2, workspaces: 0, scope: 'workbench' } })
    }
    return fail(route, 404, 'NOT_FOUND')
  })
  return { state, requests }
}

test('未接通身份时明确提示，匿名访问回到登录，无工作数据与假登录', async ({ page }) => {
  const { requests } = await mockApi(page, { authenticated: false, configured: false })
  await page.goto('/')
  await expect(page).toHaveURL(/\/login\?redirect=/)
  await expect(page.getByText('训练营身份接入尚未配置', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: '使用训练营账号继续' })).toBeDisabled()
  expect(requests.some(({ path }) => path === '/api/workspaces')).toBe(false)
})

test('管理页登录后回跳；会话凭据不写入浏览器存储', async ({ page }) => {
  await mockApi(page, { authenticated: false, permissions: ['governance:view'] })
  await page.goto('/manage')
  await expect(page).toHaveURL(/\/login\?redirect=\/manage/)
  await page.getByRole('button', { name: '使用训练营账号继续' }).click()
  await expect(page).toHaveURL('/manage')
  await expect(page.getByRole('heading', { name: '管理授权已验证' })).toBeVisible()
  expect(await page.evaluate(() => Object.keys(localStorage))).toEqual([])
  expect(await page.evaluate(() => Object.keys(sessionStorage))).toEqual([])
})

test('拒绝外部登录回跳地址', async ({ page }) => {
  await mockApi(page, { authenticated: false })
  await page.goto('/login?redirect=https%3A%2F%2Fexample.com%2F')
  await page.getByRole('button', { name: '使用训练营账号继续' }).click()
  await expect(page).toHaveURL('/')
  await expect(page.getByRole('heading', { name: '还没有加入工作空间' })).toBeVisible()
})

test('有效社团身份可以查看空态，管理入口要求明确本地授权', async ({ page }) => {
  const { requests } = await mockApi(page)
  await page.goto('/')
  await expect(page.getByRole('heading', { name: '小林，欢迎回来' })).toBeVisible()
  await expect(page.getByText('社团身份有效', { exact: true })).toBeVisible()
  await expect(page.getByRole('link', { name: '工作台管理', exact: true })).toHaveCount(0)
  await page.goto('/manage')
  await expect(page.getByRole('heading', { name: '你没有此管理权限' })).toBeVisible()
  expect(requests.some(({ path }) => path === '/api/admin/overview')).toBe(false)
})

test('社团资格失效使用403专门页面，不伪装成未登录', async ({ page }) => {
  await mockApi(page, { meError: [403, 'ADMISSION_DENIED'] })
  await page.goto('/')
  await expect(page).toHaveURL(/\/access/)
  await expect(page.getByRole('heading', { name: '暂未获得工作台访问资格' })).toBeVisible()
  await expect(page.getByRole('button', { name: '使用训练营账号继续' })).toHaveCount(0)
})

test('上游不可用屏蔽工作内容，保留已知身份而不宣称退出', async ({ page }) => {
  const { state } = await mockApi(page)
  await page.goto('/')
  await expect(page.getByRole('heading', { name: '还没有加入工作空间' })).toBeVisible()
  state.workspaceError = [503, 'IDENTITY_PROVIDER_UNAVAILABLE']
  await page.getByRole('button', { name: '刷新', exact: true }).click()
  await expect(page.getByRole('heading', { name: '暂时无法核验身份' })).toBeVisible()
  await expect(page.getByText('小林', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: '退出工作台' })).toBeVisible()
  await expect(page.getByRole('heading', { name: '还没有加入工作空间' })).toHaveCount(0)
  state.workspaceError = null
  await page.getByRole('button', { name: '重新核验身份' }).click()
  await expect(page.getByRole('heading', { name: '还没有加入工作空间' })).toBeVisible()
})

test('会话过期401回到登录并清除内存身份', async ({ page }) => {
  const { state } = await mockApi(page)
  await page.goto('/')
  await expect(page.getByRole('heading', { name: '还没有加入工作空间' })).toBeVisible()
  state.workspaceError = [401, 'SESSION_REVOKED']
  state.authenticated = false
  await page.getByRole('button', { name: '刷新', exact: true }).click()
  await expect(page).toHaveURL(/\/login/)
  await expect(page.getByText('小林', { exact: true })).toHaveCount(0)
})

test('退出使用CSRF；失败不能显示已退出', async ({ page }) => {
  const { state, requests } = await mockApi(page, { logoutError: [503, 'SERVICE_UNAVAILABLE'] })
  await page.goto('/')
  await page.getByRole('button', { name: '退出工作台' }).click()
  await expect(page.getByRole('alert')).toContainText('退出未完成')
  await expect(page.getByText('小林', { exact: true })).toBeVisible()
  state.logoutError = null
  await page.getByRole('button', { name: '退出工作台' }).click()
  await expect(page).toHaveURL('/login')
  const logoutRequest = requests.find(({ path }) => path === '/api/auth/logout')
  expect(logoutRequest.headers['x-csrf-token']).toBe('test-csrf-token')
})

test('回调资格错误显示专用提示，不回显任意query文案', async ({ page }) => {
  await mockApi(page, { authenticated: false })
  await page.goto('/login?error=ADMISSION_DENIED')
  await expect(page.getByRole('heading', { name: '暂未获得工作台访问资格' })).toBeVisible()
  await page.goto('/login?error=untrusted-arbitrary-content')
  await expect(page.getByRole('alert')).toContainText('本次身份验证未完成')
  await expect(page.getByText('untrusted-arbitrary-content')).toHaveCount(0)
})

test('手机导航可展开和关闭，页面没有横向溢出', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await mockApi(page, { permissions: ['governance:view'] })
  await page.goto('/')
  await expect(page.getByRole('heading', { name: '还没有加入工作空间' })).toBeVisible()
  await expect(page.getByRole('navigation')).not.toBeVisible()
  await page.getByRole('button', { name: '切换导航' }).click()
  await expect(page.getByRole('navigation')).toBeVisible()
  await page.getByRole('link', { name: '工作台管理', exact: true }).click()
  await expect(page.getByRole('heading', { name: '管理授权已验证' })).toBeVisible()
  await expect(page.getByRole('navigation')).not.toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})
