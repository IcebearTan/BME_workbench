import { test, expect } from '@playwright/test'

const record = { id: 1, title: '软件组组长', department: '软件组', status: 'active', term_start: '2025-09-01',
  term_end: null, record_source: 'system', years: [2025, 2026], date_precision: 'day',
  events: [{ id: 1, kind: 'officer_appointed', occurred_at: '2025-09-02T12:00:00', detail: {} }] }
const unknown = { id: 2, title: '历任副社长', status: 'ended', record_source: 'backfill', source_note: '2025届任命名单',
  historical_year: 2025, date_precision: 'year', years: [2025], events: [] }

async function mock(page, { governance = false, unavailable = false, noWorkspace = false } = {}) {
  await page.route(url => url.pathname.startsWith('/api/'), route => {
    const url = new URL(route.request().url())
    if (url.pathname === '/api/auth/me') return route.fulfill({ json: { actor: { subject: '1', display_name: '成员甲' },
      admission: { community_active: true }, permissions: governance ? ['governance:view'] : [], csrf_token: 'isolated-csrf' } })
    if (url.pathname === '/api/work/me') return route.fulfill({ json: { code: 200, data: { eligibility: { kind: 'member' }, workspaces: noWorkspace ? [] : [{ id: 1, group_name: '软件组', role: 'member' }] } } })
    if (url.pathname === '/api/appointments/history') {
      if (unavailable) return route.fulfill({ status: 503, json: { error: { message: '身份服务暂不可用' } } })
      const year = Number(url.searchParams.get('year'))
      return route.fulfill({ json: { code: 200, data: { username: '成员甲', years: [2026, 2025], undated_count: 0,
        can_select_person: governance, people: governance ? [{ id: 1, name: '成员甲' }, { id: 2, name: '成员乙' }] : [],
        records: [record, unknown].filter(r => !year || r.years.includes(year)) } } })
    }
    return route.fulfill({ json: { code: 200, data: {}, items: [], unread: 0 } })
  })
}

test('个人履历按覆盖年份展示，未知日期与历史来源保留', async ({ page }) => {
  const errors = []
  page.on('pageerror', e => errors.push(e.message))
  await mock(page)
  await page.goto('/work/appointments')
  await expect(page.getByRole('heading', { name: '任职履历', exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: '软件组组长' })).toHaveCount(2)
  await expect(page.getByText('仅确认 2025 年任职，具体日期不详。')).toBeVisible()
  await expect(page.getByText('资料来源：2025届任命名单')).toBeVisible()
  await expect(page.getByRole('combobox', { name: '选择人员' })).toHaveCount(0)
  await page.screenshot({ path: 'test-results/appointment-history-desktop.png', fullPage: true })
  await page.getByRole('combobox', { name: '选择年份' }).focus()
  await page.getByRole('combobox', { name: '选择年份' }).press('ArrowDown')
  await page.getByRole('option', { name: '2025 年' }).click()
  await expect(page).toHaveURL(/year=2025/)
  await expect(page.getByRole('heading', { name: '软件组组长' })).toHaveCount(1)
  expect(errors).toEqual([])
})

test('管理权限可选择人员，并在窄屏显示履历', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await mock(page, { governance: true })
  await page.goto('/work/appointments')
  await page.getByRole('combobox', { name: '选择人员' }).click()
  await page.getByRole('option', { name: '成员乙 · #2' }).click()
  await expect(page).toHaveURL(/user_id=2/)
  await expect(page.getByRole('heading', { name: '任职履历', exact: true })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await page.screenshot({ path: 'test-results/appointment-history-mobile.png', fullPage: true })
})

test('上游失败显示失败状态，不显示空履历或旧记录', async ({ page }) => {
  await mock(page, { unavailable: true })
  await page.goto('/work/appointments')
  await expect(page.getByRole('alert')).toContainText('身份服务暂不可用')
  await expect(page.getByRole('heading', { name: '软件组组长' })).toHaveCount(0)
  await expect(page.getByText('该年份暂无已登记的任职记录')).toHaveCount(0)
})

test('有工作台准入但没有工作区授权时仍可查看自己的任职履历', async ({ page }) => {
  await mock(page, { noWorkspace: true })
  await page.goto('/work/appointments')
  await expect(page.getByRole('heading', { name: '任职履历', exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: '软件组组长' })).toHaveCount(2)
  await expect(page.getByRole('link', { name: '小组事项', exact: true })).toHaveCount(0)
})
