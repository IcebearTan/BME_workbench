import { test, expect } from '@playwright/test'

async function mockWorkbench(page, { kind = 'task', inviteFailure = false } = {}) {
  const invitations = []
  const handoffs = []
  const detail = { id: 1, workspace_id: 1, group_name: '软件组', kind, title: '开放日活动协作', body: '共同准备开放日',
    visibility: 'participants', status: kind === 'task' ? 'todo' : 'open', created_by: 1, created_by_name: '发起成员',
    version: 2, participants: [], files: [], business_links: [], allowed_actions: ['reply', 'edit', 'invite', ...(kind === 'task' ? ['handoff'] : ['promote'])],
    task: kind === 'task' ? { assignee_user_id: 1, assignee_name: '发起成员', due_at: '2030-01-01 23:59', priority: 'normal' } : undefined }
  const candidates = [{ user_id: 2, username: '跨组甲', groups: [{ id: 2, name: '文宣组' }, { id: 3, name: '活动组' }] },
    { user_id: 3, username: '跨组乙', groups: [{ id: 2, name: '文宣组' }] }]
  let failOnce = inviteFailure
  await page.route((url) => url.pathname.startsWith('/api/'), route => {
    const request = route.request(), path = new URL(request.url()).pathname, method = request.method()
    const ok = data => route.fulfill({ json: { code: 200, data } })
    if (path === '/api/auth/me') return route.fulfill({ json: { actor: { id: 1, subject: '1', display_name: '发起成员' }, admission: { community_active: true }, permissions: [], csrf_token: 'csrf-test' } })
    if (path === '/api/work/me') return ok({ eligibility: { kind: 'member' }, workspaces: [{ id: 1, group_name: '软件组', role: 'coordinator' }], available_targets: [{ ws_id: 1, group_name: '软件组' }, { ws_id: 2, group_name: '文宣组' }], todo: {} })
    if (path === '/api/notifications') return route.fulfill({ json: { items: [], unread: 0 } })
    if (path === '/api/work/candidates') return ok({ candidates })
    if (path === '/api/work/items/1') return ok(detail)
    if (path === '/api/work/items/1/participants' && method === 'POST') {
      const body = request.postDataJSON()
      invitations.push(body.user_id)
      expect(request.headers()['x-csrf-token']).toBe('csrf-test')
      if (failOnce && body.user_id === 3) { failOnce = false; return route.fulfill({ status: 400, json: { message: '该成员当前不可加入' } }) }
      detail.participants.push({ ...candidates.find(c => c.user_id === body.user_id), ptype: body.ptype })
      return ok({ id: 1 })
    }
    if (path === '/api/work/items/1/handoffs') {
      if (method === 'GET') return ok({ outgoing: handoffs, incoming: [] })
      const body = request.postDataJSON()
      handoffs.push({ ...body, id: 7, item_id: 1, to_group_name: '文宣组', status: 'offered', can_withdraw: true, can_read_target: false })
      return ok({ handoff_id: 7 })
    }
    if (path === '/api/work/handoffs/7/withdraw') { handoffs[0].status = 'withdrawn'; handoffs[0].can_withdraw = false; return ok({}) }
    return ok({ items: [], replies: [], events: [], types: [], handoffs: [], total: 0 })
  })
  return { invitations, handoffs }
}

test('跨组邀请支持按多组归属筛选，多人部分失败后仅重试未成功者', async ({ page }) => {
  const state = await mockWorkbench(page, { kind: 'topic', inviteFailure: true })
  await page.goto('/work/items/1')
  await page.getByRole('button', { name: '邀请成员一起协作', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await dialog.locator('.el-select__wrapper').nth(0).click()
  await page.getByRole('option', { name: '活动组', exact: true }).click()
  await dialog.locator('.el-select__wrapper').nth(1).click()
  await expect(page.getByRole('option', { name: /跨组甲/ })).toBeVisible()
  await expect(page.getByRole('option', { name: /跨组乙/ })).toHaveCount(0)
  await page.getByRole('option', { name: /跨组甲/ }).click()
  await dialog.getByText('参与方式', { exact: true }).click()
  await dialog.locator('.el-select__wrapper').nth(0).click()
  await page.getByRole('option', { name: '文宣组', exact: true }).click()
  await dialog.locator('.el-select__wrapper').nth(1).click()
  await page.getByRole('option', { name: /跨组乙/ }).click()
  await dialog.getByText('参与方式', { exact: true }).click()
  await dialog.getByRole('button', { name: '邀请所选成员' }).click()
  await expect(dialog.getByRole('alert')).toContainText('跨组乙：该成员当前不可加入')
  await dialog.getByRole('button', { name: '邀请所选成员' }).click()
  await expect(dialog).toHaveCount(0)
  expect(state.invitations).toEqual([2, 3, 3])
  await expect(page.locator('.participant-row').filter({ hasText: '跨组甲' })).toBeVisible()
  await expect(page.locator('.participant-row').filter({ hasText: '跨组乙' })).toBeVisible()
})

test('跨组交付不列当前组，刷新后仍能查看进度和撤回', async ({ page }) => {
  const state = await mockWorkbench(page)
  await page.goto('/work/items/1')
  await page.getByRole('button', { name: '请其他组承接', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await dialog.locator('.el-select__wrapper').first().click()
  await expect(page.getByRole('option', { name: '软件组', exact: true })).toHaveCount(0)
  await page.getByRole('option', { name: '文宣组', exact: true }).click()
  await dialog.locator('textarea').fill('请准备开放日海报，周五确认初稿。')
  await dialog.getByRole('button', { name: '确认执行' }).click()
  await expect(page.locator('.handoff-row')).toContainText('待对方接单')
  expect(state.handoffs[0].to_workspace_id).toBe(2)
  await page.reload()
  await expect(page.locator('.handoff-row')).toContainText('请准备开放日海报')
  await expect(page.getByRole('button', { name: '查看承接任务' })).toHaveCount(0)
  await page.screenshot({ path: 'test-results/cross-group-detail.png', fullPage: true })
  await page.getByRole('button', { name: '撤回交付' }).click()
  await page.getByRole('button', { name: '撤回', exact: true }).click()
  await expect(page.locator('.handoff-row')).toContainText('已撤回')
  await expect(page.getByRole('button', { name: '撤回交付' })).toHaveCount(0)
})

test('交付进度读取失败明确显示重试，不显示空记录', async ({ page }) => {
  await mockWorkbench(page)
  await page.route('**/api/work/items/1/handoffs', route => route.fulfill({ status: 503, json: { message: '服务暂不可用' } }))
  await page.goto('/work/items/1')
  await expect(page.getByRole('alert')).toContainText('交付进度加载失败')
  await expect(page.getByText('暂无跨组交付。', { exact: false })).toHaveCount(0)
})
