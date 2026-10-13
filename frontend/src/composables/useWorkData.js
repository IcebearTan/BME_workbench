// 内部工作台共享数据 — 模块级单例（范式对齐 useNotifications）。
// 承载待办计数（/work/me 摘要轮询：活动页 30s、隐藏页暂停，§7.5 适度轮询）。
// 工作区列表唯一来源是 useWorkAccess.me（探测结果），这里不再留第二份副本防发散；
// 事项列表/详情等页面级数据由各组件自持，不进单例（避免跨页污染）。
import { ref } from 'vue'
import { workService } from '../services/workService'

// ── 模块级单例状态 ──
const todoCounts = ref({
  pending_responses: 0, pending_transfers: 0,
  to_review: 0, due_soon: 0, overdue: 0,
})
let pollTimer = null

export function useWorkData() {
  /** 刷新待办摘要（探测失败的入口场景由 useWorkAccess 负责，这里静默） */
  async function refreshSummary() {
    const res = await workService.fetchMe()
    const data = res?.data || {}
    if (data.todo) todoCounts.value = data.todo
  }

  /** 摘要轮询：仅页面可见时打点；重复调用不叠加计时器 */
  function startSummaryPolling() {
    if (pollTimer) return
    pollTimer = setInterval(() => {
      if (document.visibilityState === 'visible') {
        refreshSummary().catch(() => {})
      }
    }, 30000)
  }

  function stopSummaryPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  return { todoCounts, refreshSummary, startSummaryPolling, stopSummaryPolling }
}

/** 生成回复幂等键（客户端请求 ID，§7.5：同键重试回原结果） */
export function newClientRequestId() {
  return (crypto?.randomUUID?.() || `cr-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`)
}
