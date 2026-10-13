// 内部工作台服务层 — 唯一对接后端 /work 蓝图的入口（feature/work-collab）
// M1：资格探测/工作区；M2：事项/回复/参与者/已读/事件/待办；M4 扩文件。
import api from '../api'

// 事项可见范围文案（后端 visibility：workspace=本工作区可见 / participants=仅参与人）
export const VISIBILITY_LABELS = {
  workspace: '本组可见',
  participants: '仅参与人可见',
}

// 事项状态文案（topic: draft/open/closed；task 状态集 M3 命令上线后启用）
export const ITEM_STATUS_LABELS = {
  draft: '草稿',
  open: '进行中',
  closed: '已关闭',
  todo: '待执行',
  in_progress: '进行中',
  blocked: '受阻',
  review: '待验收',
  done: '已完成',
  cancelled: '已取消',
}

// 状态 → DewTag/ElTag 语义色（进行中系=primary、完成=success、受阻/逾期=danger）
export const ITEM_STATUS_TYPE = {
  draft: 'info', open: 'primary', closed: 'info',
  todo: 'warning', in_progress: 'primary', blocked: 'danger',
  review: 'warning', done: 'success', cancelled: 'info',
}

// 工作事件类型文案（时间线渲染；与后端 events 白名单同源）
export const EVENT_LABELS = {
  created: '创建了事项',
  published: '发布了事项',
  edited: '编辑了事项',
  replied: '回复了事项',
  closed: '关闭了事项',
  reopened: '重新打开了事项',
  promoted: '转为任务',
  assigned: '调整了负责人',
  transfer_requested: '发起转交',
  transfer_accepted: '接受了转交',
  status_changed: '状态变更',
  due_changed: '调整了截止时间',
  priority_changed: '调整了优先级',
  submitted: '提交了结果',
  reviewed: '完成了验收',
  participant_added: '加入了参与者',
  participant_removed: '移除了参与者',
  file_attached: '添加了附件',
  visibility_changed: '调整了可见范围',
  emergency_access: '治理紧急介入',
}

export const workService = {
  /** 资格与工作台摘要（探测端点：无资格回 200 空形，前端据此隐藏入口） */
  async fetchMe() {
    return api.get('/work/me').then(r => r.data)
  },

  /** 我可进入的工作区列表 */
  async fetchWorkspaces() {
    return api.get('/work/workspaces').then(r => r.data)
  },

  /** 事项列表（kind/status/workspace/mine/q 筛选，服务端分页） */
  async fetchItems(params = {}) {
    return api.get('/work/items', { params }).then(r => r.data)
  },

  /** 创建话题/任务草稿（幂等键去重；发布走 runCommand('publish')） */
  async createItem(payload) {
    return api.post('/work/items', payload).then(r => r.data)
  },

  /** 事项详情（含 allowed_actions 与参与者） */
  async fetchItem(id) {
    return api.get(`/work/items/${id}`).then(r => r.data)
  },

  /** 编辑标题/正文/可见范围（expected_version 乐观锁） */
  async patchItem(id, payload) {
    return api.patch(`/work/items/${id}`, payload).then(r => r.data)
  },

  /** 回复时间线（after_seq 游标增量拉取） */
  async fetchReplies(id, params = {}) {
    return api.get(`/work/items/${id}/replies`, { params }).then(r => r.data)
  },

  /** 发送回复（client_request_id 幂等） */
  async sendReply(id, payload) {
    return api.post(`/work/items/${id}/replies`, payload).then(r => r.data)
  },

  /** 命令（publish/close/reopen/promote + 任务命令表：start/block/unblock/submit/complete/review_accept/review_return/reschedule/reassign/cancel/reopen） */
  async runCommand(id, payload) {
    return api.post(`/work/items/${id}/commands`, payload).then(r => r.data)
  },

  /** 移除业务关联 */
  async removeLink(itemId, sourceType, sourceId) {
    return api.delete('/work/items/' + itemId + '/links', {
      data: { source_type: sourceType, source_id: sourceId },
    }).then(r => r.data)
  },

  /** 工作区看板：按关联对象聚合本组事项态势（X2 通用投影） */
  async fetchBoard(wsId) {
    return api.get('/work/objects/board', { params: { ws: wsId } }).then(r => r.data)
  },

  /** 认领/取消认领对象维护责任（协调员；幂等） */
  async claimObject(payload) {
    return api.post('/work/objects/claim', payload).then(r => r.data)
  },

  /** 可关联类型目录（注册表驱动） */
  async fetchObjectTypes() {
    return api.get('/work/objects/types').then(r => r.data)
  },

  /** 发起跨组交付（X1：目标组接单后在本组生成关联任务） */
  async createHandoff(itemId, payload) {
    return api.post(`/work/items/${itemId}/handoffs`, payload).then(r => r.data)
  },

  /** 接单/拒绝/撤回跨组交付（accept|decline|withdraw） */
  async decideHandoff(handoffId, action, payload = {}) {
    return api.post(`/work/handoffs/${handoffId}/${action}`, payload).then(r => r.data)
  },

  /** 子组摘要列表（subtree 授权者；仅标题/状态/负责人/截止，无正文） */
  async fetchSummaryItems(params = {}) {
    return api.get('/work/items', { params: { ...params, rollup: 'subtree' } }).then(r => r.data)
  },

  /** 发起负责人转交（§8.4：对方确认后才替换负责人） */
  async createTransfer(id, payload) {
    return api.post(`/work/items/${id}/transfers`, payload).then(r => r.data)
  },

  /** 接受/拒绝/撤回转交（accept|reject|withdraw） */
  async decideTransfer(transferId, action) {
    return api.post(`/work/transfers/${transferId}/${action}`).then(r => r.data)
  },

  /** 邀请候选人与任务负责人选择源（仅返回有协作资格者） */
  async fetchCandidates() {
    return api.get('/work/candidates').then(r => r.data)
  },

  /** 上传附件（multipart；fileId 传则为既有文件传新版本） */
  async uploadFile(itemId, file, fileId = null) {
    const form = new FormData()
    form.append('file', file)
    if (fileId) form.append('file_id', String(fileId))
    return api.post(`/work/items/${itemId}/files`, form).then(r => r.data)
  },

  /** 文件版本列表 */
  async fetchFileVersions(fileId) {
    return api.get(`/work/files/${fileId}/versions`).then(r => r.data)
  },

  /** 「工作资料」附件索引（跨可见事项聚合，文件名检索） */
  async searchFiles(params = {}) {
    return api.get('/work/files', { params }).then(r => r.data)
  },

  /** 鉴权下载（fetch-blob 保存；撤权后 404 由调用方提示） */
  async downloadFile(fileId, linkId, filename) {
    const res = await api.get(`/work/files/${fileId}/download`, {
      params: { link_id: linkId }, responseType: 'blob' })
    const url = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = url
    a.download = filename || '附件'
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  },

  /** 建立业务关联（白名单 course/camp_session/feedback_ticket） */
  async createLink(itemId, payload) {
    return api.post(`/work/items/${itemId}/links`, payload).then(r => r.data)
  },

  /** 邀请参与者 */
  async addParticipant(id, payload) {
    return api.post(`/work/items/${id}/participants`, payload).then(r => r.data)
  },

  /** 移除参与者 */
  async removeParticipant(id, userId, reason) {
    return api.delete(`/work/items/${id}/participants/${userId}`, { data: { reason } }).then(r => r.data)
  },

  /** 推进已读游标 */
  async advanceRead(id, lastReadSeq) {
    return api.post(`/work/items/${id}/read`, { last_read_seq: lastReadSeq }).then(r => r.data)
  },

  /** 工作事件时间线 */
  async fetchEvents(id, params = {}) {
    return api.get(`/work/items/${id}/events`, { params }).then(r => r.data)
  },

  /** 我的待办分桶 */
  async fetchTodos() {
    return api.get('/work/me/todos').then(r => r.data)
  },
}
