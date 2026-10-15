import { test, expect } from '@playwright/test'

async function mock(page, { manager = false, governance = false, subtree = false, noWorkspace = false } = {}) {
  await page.route(url => url.pathname.startsWith('/api/'), route => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/auth/me') return route.fulfill({ json: {
      actor: { id: 1, subject: '1', display_name: '测试成员' }, admission: { community_active: true },
      permissions: manager ? ['governance:manage'] : [], csrf_token: 'test-csrf',
    } })
    if (path === '/api/work/me') return route.fulfill({ json: { code: 200, data: {
      is_governance: governance || manager,
      workspaces: noWorkspace ? [] : [{ id: 1, group_name: '软件组', role: subtree ? 'coordinator' : 'member', subtree }],
      todo: {},
    } } })
    if (path === '/api/appointments/history') return route.fulfill({ json: { code: 200, data: {
      user_id: 1, username: '测试成员', years: [], records: [], undated_count: 0, can_select_person: false, people: [],
    } } })
    return route.fulfill({ json: { code: 200, data: {}, items: [], unread: 0 } })
  })
}

for (const actor of [
  { name: '普通成员', options: {}, coordination: false, management: [] },
  { name: '有子组汇总权的协调员', options: { subtree: true }, coordination: true, management: [] },
  { name: '治理授权人员', options: { governance: true }, coordination: false, management: ['工作区与授权'] },
  { name: '管理员', options: { manager: true, subtree: true }, coordination: true, management: ['小组任职管理', '工作区与授权'] },
]) {
  test(`${actor.name}的侧栏分组只包含有权使用的入口`, async ({ page }, testInfo) => {
    const errors = []
    page.on('pageerror', e => errors.push(e.message))
    await mock(page, actor.options)
    await page.goto('/work/appointments')
    const nav = page.getByRole('navigation', { name: '工作台功能导航' })
    await expect(nav.getByRole('region', { name: '日常工作' }).getByRole('link')).toHaveText(['概览', '小组事项', '看板', '工作资料', '工作记录'])
    await expect(nav.getByRole('region', { name: '组织与个人' }).getByRole('link')).toHaveText(['成员', '任职履历'])
    await expect(nav.getByRole('region', { name: '小组协调' })).toHaveCount(actor.coordination ? 1 : 0)
    const management = nav.getByRole('region', { name: '管理与治理' })
    await expect(management).toHaveCount(actor.management.length ? 1 : 0)
    if (actor.management.length) await expect(management.getByRole('link')).toHaveText(actor.management)
    await expect(nav.getByRole('link', { name: '任职履历', exact: true })).toHaveAttribute('aria-current', 'page')
    await expect(page.getByRole('link', { name: '打开工作台管理', exact: true })).toHaveCount(0)
    if (actor.options.manager) await page.locator('.ws-side').screenshot({ path: testInfo.outputPath('grouped-sidebar.png') })
    expect(errors).toEqual([])
  })
}

test('无工作区授权时仅保留自己的履历分组', async ({ page }) => {
  await mock(page, { noWorkspace: true })
  await page.goto('/work/appointments')
  const nav = page.getByRole('navigation', { name: '工作台功能导航' })
  await expect(nav.getByRole('region')).toHaveCount(1)
  await expect(nav.getByRole('link')).toHaveText(['任职履历'])
})

test('移动端分组可滚动，点击导航后关闭侧栏', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await mock(page, { manager: true, subtree: true })
  await page.goto('/work/appointments')
  const toggle = page.getByRole('button', { name: '切换侧栏' })
  await toggle.click()
  await expect(toggle).toHaveAttribute('aria-expanded', 'true')
  const link = page.getByRole('navigation', { name: '工作台功能导航' }).getByRole('link', { name: '工作区与授权' })
  await link.scrollIntoViewIfNeeded()
  await expect(link).toBeInViewport()
  await page.screenshot({ path: testInfo.outputPath('mobile-grouped-sidebar.png') })
  await page.getByRole('navigation', { name: '工作台功能导航' }).getByRole('link', { name: '任职履历', exact: true }).click()
  await expect(toggle).toHaveAttribute('aria-expanded', 'false')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
})
