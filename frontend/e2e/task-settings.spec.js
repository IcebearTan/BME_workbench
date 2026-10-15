import { test, expect } from '@playwright/test'

async function mockWorkbench(page, options = {}) {
  const state = {
    creates: [], patches: [], commands: [], detailReads: 0, candidateReads: 0,
    detail: {
      id: 31, workspace_id: 1, group_name: '软件组', kind: 'task', title: '准备联合活动',
      body: '已有说明', visibility: 'workspace', status: 'draft', created_by: 1,
      created_by_name: '测试成员', version: 7, participants: [], files: [], business_links: [],
      allowed_actions: ['edit', 'publish'], last_reply_seq: 0, reply_count: 0,
      item_access: { via: 'workspace', workspace_role: 'coordinator' },
      task: { assignee_user_id: null, reviewer_user_id: null, due_at: null, priority: 'normal',
        accept_criteria: '', submissions: [], overdue: false },
      ...options.detail,
    },
  }
  await page.route((url) => url.pathname.startsWith('/api/'), async (route) => {
    const request = route.request()
    const path = new URL(request.url()).pathname
    const method = request.method()
    const ok = (data) => route.fulfill({ json: { code: 200, data } })
    if (path === '/api/auth/me') return route.fulfill({ json: {
      actor: { id: 1, subject: '1', display_name: '测试成员' }, admission: { community_active: true },
      permissions: [], csrf_token: 'test-csrf',
    } })
    if (path === '/api/work/me') return ok({ eligibility: { kind: 'member' }, is_governance: false,
      workspaces: [{ id: 1, club_group_id: 1, group_name: '软件组', role: 'coordinator' }],
      available_targets: [], todo: {},
    })
    if (path === '/api/notifications') return route.fulfill({ json: { items: [], unread: 0 } })
    if (path === '/api/work/candidates') {
      state.candidateReads += 1
      return ok({ candidates: [{ user_id: 2, username: '执行成员' }, { user_id: 3, username: '验收成员' }] })
    }
    if (path === '/api/work/items' && method === 'POST') {
      const payload = request.postDataJSON()
      state.creates.push(payload)
      if (options.createFailureOnce && state.creates.length === 1) {
        return route.fulfill({ status: 503, json: { code: 503, message: '暂时无法完成创建' } })
      }
      state.detail = { ...state.detail, ...payload, status: 'draft' }
      return ok(state.detail)
    }
    if (path === '/api/work/items') return ok({ items: [], total: 0 })
    if (path === '/api/work/items/31' && method === 'PATCH') {
      const payload = request.postDataJSON()
      state.patches.push(payload)
      if (options.conflict) {
        state.detail = { ...state.detail, title: '其他人已修改的标题', version: state.detail.version + 1 }
        return route.fulfill({ status: 409, json: { code: 409, message: '事项已更新，请刷新后重试' } })
      }
      const task = { ...state.detail.task, ...payload.task }
      task.due_at = task.due_at?.replace('T', ' ') || null
      task.assignee_name = task.assignee_user_id === 2 ? '执行成员' : null
      task.reviewer_name = task.reviewer_user_id === 3 ? '验收成员' : null
      state.detail = { ...state.detail, ...payload, task,
        version: state.detail.version + 1 }
      return ok(state.detail)
    }
    if (path === '/api/work/items/31') {
      state.detailReads += 1
      return ok(state.detail)
    }
    if (path === '/api/work/items/31/commands') {
      state.commands.push(request.postDataJSON())
      if (options.publishFailure) {
        return route.fulfill({ status: 409, json: { code: 409, message: '事项状态发生变化' } })
      }
      state.detail = { ...state.detail, status: state.detail.kind === 'task' ? 'todo' : 'open',
        allowed_actions: ['edit', 'invite'], version: state.detail.version + 1 }
      return ok(state.detail)
    }
    return ok({ replies: [], events: [], types: [], pending_responses: [], handoffs: [] })
  })
  return state
}

test('任务创建仅需标题，执行安排留在详情设置', async ({ page }, testInfo) => {
  const state = await mockWorkbench(page)
  await page.goto('/work/items?ws=1')
  await page.getByRole('button', { name: '发起事项' }).click()
  const dialog = page.getByRole('dialog')
  await dialog.locator('.el-radio-button__inner').filter({ hasText: /^任务$/ }).click()
  await dialog.getByPlaceholder('一句话说清这件事是什么').fill('准备联合活动')
  await expect(dialog.getByText('创建后为仅自己可见的草稿。发布前可在事项设置中调整可见范围。')).toBeVisible()
  await expect(dialog.getByPlaceholder('待分派')).toHaveCount(0)
  await expect(dialog.getByPlaceholder('待设置')).toHaveCount(0)
  await dialog.screenshot({ path: testInfo.outputPath('quick-create.png') })
  await dialog.getByRole('button', { name: '创建任务', exact: true }).click()
  await expect(page).toHaveURL(/\/work\/items\/31/)
  await expect(page.locator('.task-panel').getByText('待分派', { exact: true })).toBeVisible()
  await expect(page.locator('.task-panel').getByText('待设置', { exact: true })).toBeVisible()
  expect(state.creates).toHaveLength(1)
  expect(state.creates[0]).not.toHaveProperty('task')
  expect(state.commands).toHaveLength(0)
  expect(state.candidateReads).toBe(0)
})

test('话题创建重试复用幂等键，明确选择可见范围并使用返回版本发布', async ({ page }) => {
  const state = await mockWorkbench(page, { createFailureOnce: true })
  await page.goto('/work/items?ws=1')
  await page.getByRole('button', { name: '发起事项' }).click()
  const dialog = page.getByRole('dialog')
  await dialog.getByPlaceholder('一句话说清这件事是什么').fill('跨组讨论')
  await expect(dialog.getByText('发布后本组成员可见。', { exact: true })).toBeVisible()
  await dialog.getByRole('button', { name: '调整可见范围' }).click()
  await dialog.locator('.el-radio__label').filter({ hasText: /^仅参与人可见$/ }).click()
  await dialog.getByRole('button', { name: '发布话题', exact: true }).click()
  await expect(page.getByText('暂时无法完成创建', { exact: true })).toBeVisible()
  await dialog.getByRole('button', { name: '发布话题', exact: true }).click()
  await expect(page).toHaveURL(/\/work\/items\/31/)
  expect(state.creates).toHaveLength(2)
  expect(state.creates[0].idempotency_key).toBe(state.creates[1].idempotency_key)
  expect(state.creates[1].visibility).toBe('participants')
  expect(state.commands).toEqual([{ command: 'publish', expected_version: 7 }])
})

test('话题发布失败后进入已保存的草稿而不重复创建', async ({ page }) => {
  const state = await mockWorkbench(page, { publishFailure: true })
  await page.goto('/work/items?ws=1')
  await page.getByRole('button', { name: '发起事项' }).click()
  await page.getByPlaceholder('一句话说清这件事是什么').fill('需继续整理的话题')
  await page.getByRole('button', { name: '发布话题', exact: true }).click()
  await expect(page).toHaveURL(/\/work\/items\/31/)
  await expect(page.getByText('草稿已保存，但发布失败：事项状态发生变化', { exact: true })).toBeVisible()
  expect(state.creates).toHaveLength(1)
  expect(state.detail.status).toBe('draft')
})

test('事项设置仅提交变更，可清空正文与草稿可选值', async ({ page }) => {
  const state = await mockWorkbench(page, { detail: {
    task: { assignee_user_id: 2, assignee_name: '执行成员', reviewer_user_id: 3,
      reviewer_name: '验收成员', due_at: '2026-10-20 16:00', priority: 'normal',
      accept_criteria: '提供活动总结', submissions: [] },
  } })
  await page.goto('/work/items/31')
  await page.getByRole('button', { name: '事项设置', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await dialog.getByPlaceholder('补充完整说明，支持 Markdown').fill('')
  await dialog.getByPlaceholder('怎样算完成（选填）').fill('')
  const assignee = dialog.locator('.el-form-item').filter({ has: page.locator('.el-form-item__label', { hasText: /^负责人$/ }) })
  await assignee.locator('.el-select').hover()
  await assignee.locator('.el-select__clear').click()
  const due = dialog.getByPlaceholder('待设置')
  await due.hover()
  await due.locator('..').locator('.clear-icon').click()
  await dialog.getByRole('button', { name: '保存设置', exact: true }).click()
  await expect(page.locator('.dew-dialog')).toBeHidden()
  expect(state.patches).toEqual([{ expected_version: 7, body: '',
    task: { assignee_user_id: null, due_at: null, accept_criteria: null } }])
})

test('设置遇到版本冲突刷新详情，并保留编辑内容和原始版本', async ({ page }) => {
  const state = await mockWorkbench(page, { conflict: true })
  await page.goto('/work/items/31')
  await page.getByRole('button', { name: '事项设置', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await dialog.getByPlaceholder('事项标题').fill('我的未保存标题')
  await dialog.getByRole('button', { name: '保存设置', exact: true }).click()
  await expect(dialog.getByRole('alert')).toContainText('当前输入已保留')
  await expect(dialog.getByPlaceholder('事项标题')).toHaveValue('我的未保存标题')
  await expect(dialog.getByRole('button', { name: '保存设置', exact: true })).toBeDisabled()
  await expect(page.getByRole('heading', { name: '其他人已修改的标题', exact: true })).toBeVisible()
  expect(state.detailReads).toBeGreaterThan(1)
  expect(state.patches).toEqual([{ expected_version: 7, title: '我的未保存标题' }])
})

test('待验收任务设置保留验收约定，仅修改优先级', async ({ page }) => {
  const state = await mockWorkbench(page, { detail: {
    status: 'review', allowed_actions: ['edit', 'review_accept', 'review_return'],
    task: { assignee_user_id: 2, reviewer_user_id: 3, due_at: '2026-10-20 16:00',
      priority: 'normal', accept_criteria: '提供活动总结', submissions: [] },
  } })
  await page.goto('/work/items/31')
  await page.getByRole('button', { name: '事项设置', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await expect(dialog.getByPlaceholder('怎样算完成（选填）')).toBeDisabled()
  await expect(dialog.getByPlaceholder('待分派')).toHaveCount(0)
  await expect(dialog.getByPlaceholder('待设置')).toHaveCount(0)
  await dialog.locator('.el-radio__label').filter({ hasText: /^高$/ }).click()
  await dialog.getByRole('button', { name: '保存设置', exact: true }).click()
  await expect(dialog).toBeHidden()
  expect(state.patches).toEqual([{ expected_version: 7, task: { priority: 'high' } }])
})

test('草稿通过事项设置补齐安排后可发布为待执行任务', async ({ page }, testInfo) => {
  const state = await mockWorkbench(page)
  await page.goto('/work/items/31')
  await expect(page.getByRole('button', { name: '发布', exact: true })).toHaveCount(0)
  await page.getByRole('button', { name: '完善任务设置', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await dialog.getByRole('combobox', { name: '负责人', exact: true }).click()
  await page.getByRole('option', { name: '执行成员', exact: true }).click()
  const due = dialog.getByPlaceholder('待设置')
  await due.fill('2026-10-20 16:00')
  await due.press('Enter')
  await dialog.getByPlaceholder('事项标题').click()
  await page.locator('.dew-dialog').screenshot({ path: testInfo.outputPath('task-settings.png') })
  await dialog.getByRole('button', { name: '保存设置', exact: true }).click()
  await expect(page.locator('.dew-dialog')).toBeHidden()
  await expect(page.locator('.task-panel').getByText('执行成员', { exact: true })).toBeVisible()
  await expect(page.locator('.task-panel').getByText('2026-10-20 16:00', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: '发布', exact: true }).click()
  await page.getByRole('button', { name: '确认', exact: true }).click()
  await expect(page.locator('.title-line').getByText('待执行', { exact: true })).toBeVisible()
  expect(state.patches).toEqual([{ expected_version: 7, task: { assignee_user_id: 2, due_at: '2026-10-20T16:00' } }])
  expect(state.commands).toEqual([{ command: 'publish', expected_version: 8 }])
})
