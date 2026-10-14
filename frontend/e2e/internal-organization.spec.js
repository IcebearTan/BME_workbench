import { test, expect } from '@playwright/test'

test('管理员可将认证人员登记为多个组的分管核心，写请求携带CSRF', async ({ page }) => {
  let saved = null
  const errors = []
  page.on('pageerror', e => errors.push(e.message))
  await page.route(url => url.pathname.startsWith('/api/'), route => {
    const request = route.request(), path = new URL(request.url()).pathname
    if (path === '/api/auth/me') return route.fulfill({ json: { actor: { id: 1, subject: '1', display_name: '工作台管理者' }, admission: { community_active: true }, permissions: ['governance:manage'], csrf_token: 'test-csrf' } })
    if (path === '/api/work/me') return route.fulfill({ json: { code: 200, data: { is_governance: true, workspaces: [] } } })
    if (path === '/api/admin/organization/candidates') return route.fulfill({ json: { code: 200, data: { matches: [{ status: 'unique_matched', resolved_user_id: 2, resolved_account: { eligible: true }, candidates: [{ person_id: 22, verified_name: '认证成员' }] }] } } })
    if (path === '/api/admin/organization/members' && request.method() === 'POST') {
      saved = request.postDataJSON()
      expect(request.headers()['x-csrf-token']).toBe('test-csrf')
      return route.fulfill({ json: { code: 200, data: { results: [] } } })
    }
    if (path === '/api/admin/organization/members') return route.fulfill({ json: { code: 200, data: { members: [], groups: [{ id: 1, name: '真实项目组' }, { id: 2, name: '竞赛项目组' }, { id: 3, name: '科普游学组' }] } } })
    return route.fulfill({ json: { code: 200, data: {}, items: [], unread: 0 } })
  })
  await page.goto('/work/organization')
  await page.getByRole('button', { name: '登记小组任职' }).click()
  const dialog = page.getByRole('dialog', { name: '登记小组任职' })
  await dialog.getByPlaceholder('输入核验姓名').fill('认证成员')
  await dialog.getByRole('button', { name: '核对账号' }).click()
  await expect(dialog.getByText('已确认：认证成员')).toBeVisible()
  await dialog.locator('.el-select').click()
  for (const group of ['真实项目组', '竞赛项目组', '科普游学组']) await page.getByRole('option', { name: group, exact: true }).click()
  await page.keyboard.press('Escape')
  await dialog.getByText('分管核心', { exact: true }).click()
  await dialog.getByRole('textbox', { name: '登记原因' }).fill('正式名单录入')
  await page.screenshot({ path: 'test-results/internal-organization-form.png' })
  await dialog.getByRole('button', { name: '保存任职' }).click()
  await expect(dialog).not.toBeVisible()
  expect(saved.entries).toHaveLength(3)
  expect(saved.entries.every(e => e.user_id === 2 && e.person_id === 22 && e.role === 'coordinator')).toBe(true)
  expect(errors).toEqual([])
})

test('没有成员管理权限时无法打开任职管理页面', async ({ page }) => {
  await page.route(url => url.pathname.startsWith('/api/'), route => route.fulfill({ json: { actor: { subject: '1', display_name: '普通成员' }, admission: { community_active: true }, permissions: [], csrf_token: 'test-csrf' } }))
  await page.goto('/work/organization')
  await expect(page).toHaveURL(/forbidden/)
})
