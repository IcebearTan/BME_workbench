import { test, expect } from '@playwright/test'

test('迁入的事项页面可创建话题，写请求携带工作台CSRF', async ({ page }) => {
  let created = false
  const writes = []
  const detail = { id: 1, workspace_id: 1, group_name: '软件组', kind: 'topic', title: '新协作事项', body: '',
    visibility: 'workspace', status: 'open', created_by: 1, version: 2, participants: [], files: [], business_links: [],
    allowed_actions: ['reply', 'edit', 'close', 'invite'], item_access: { via: 'workspace', workspace_role: 'coordinator' } }
  await page.route((url) => url.pathname.startsWith('/api/'), (route) => {
    const request = route.request(), path = new URL(request.url()).pathname
    if (request.method() === 'POST') writes.push({ path, csrf: request.headers()['x-csrf-token'], body: request.postDataJSON() })
    if (path === '/api/auth/me') return route.fulfill({ json: { actor: { id: 1, subject: '1', display_name: '测试成员' }, admission: { community_active: true }, permissions: [], csrf_token: 'test-csrf' } })
    if (path === '/api/work/me') return route.fulfill({ json: { code: 200, data: { eligibility: { kind: 'member' }, is_governance: false, workspaces: [{ id: 1, club_group_id: 1, group_name: '软件组', role: 'coordinator' }], todo: {} } } })
    if (path === '/api/notifications') return route.fulfill({ json: { items: [], unread: 0 } })
    if (path === '/api/work/candidates') return route.fulfill({ json: { code: 200, data: { candidates: [] } } })
    if (path === '/api/work/items' && request.method() === 'POST') { created = true; return route.fulfill({ json: { code: 200, data: { ...detail, status: 'draft', version: 1 } } }) }
    if (path === '/api/work/items') return route.fulfill({ json: { code: 200, data: { items: [], total: 0 } } })
    if (path === '/api/work/items/1') return route.fulfill({ json: { code: 200, data: detail } })
    return route.fulfill({ json: { code: 200, data: { replies: [], events: [], types: [], id: 1, version: 2 } } })
  })
  await page.goto('/work/items?ws=1')
  await page.getByRole('button', { name: '发起事项' }).click()
  await page.getByPlaceholder('一句话说清这件事是什么').fill('新协作事项')
  await page.getByRole('button', { name: '发布话题' }).click()
  await expect(page).toHaveURL(/\/work\/items\/1/)
  await expect(page.getByRole('heading', { name: '新协作事项' })).toBeVisible()
  expect(created).toBe(true)
  expect(writes.every((request) => request.csrf === 'test-csrf')).toBe(true)
})
