// 内部工作台资格探测 — 模块级单例状态（范式对齐 useNotificationTabs 的导生探测）。
// /work/me 是探测端点：无资格回 200 空形；探测失败静默（仅失去入口，不影响页面主流程）。
// 消费方：服务台入口卡 / 顶栏入口 / 组织架构页「进入工作区」按钮 / 通知中心「工作」tab。
import { ref } from 'vue'
import { store } from '../store/index.js'
import { workService } from '../services/workService'

// ── 模块级单例状态（所有 useWorkAccess() 实例共享） ──
const me = ref(null)
const hasAccess = ref(false)
const isGovernance = ref(false)
const detecting = ref(false)
const detectFailed = ref(false)
let probe = null      // 探测成功后按 TTL 复用；失败置空允许下次重试（登出/换号后可 force）
let probedAt = 0      // 最近一次探测成功时间戳（TTL 计时起点）
const PROBE_TTL_MS = 5 * 60 * 1000   // 资格变更最长 5 分钟内生效（与服务端「下一请求失效」在入口层对齐）

export function useWorkAccess() {
  function detect(force = true) {
    const fresh = probe && Date.now() - probedAt < PROBE_TTL_MS
    if (!force && fresh) return probe
    const token = store.getters.authenticated
    if (!token) {                                 // 未登录：清空单例态，不发请求
      me.value = null
      hasAccess.value = false
      isGovernance.value = false
      detectFailed.value = false
      probe = null
      probedAt = 0
      return Promise.resolve()
    }
    detecting.value = true
    detectFailed.value = false
    probe = workService.fetchMe()
      .then((res) => {
        const data = res?.data || {}
        me.value = data
        // 入口判据：有可进入的工作区，或持有治理身份（治理人员可能暂无组工作区）
        hasAccess.value = Boolean(data.workspaces?.length) || Boolean(data.is_governance)
        isGovernance.value = Boolean(data.is_governance)
        probedAt = Date.now()   // 成功也记时戳：TTL 过期后下一次 detect 自动重探
      })
      .catch(() => { probe = null; detectFailed.value = true })
      .finally(() => { detecting.value = false })
    return probe
  }

  /** 组织架构页组卡片用：该组是否是我可进入的工作区（按 club_group_id 匹配，不发额外请求） */
  function workspaceForGroup(groupId) {
    return (me.value?.workspaces || []).find(w => w.club_group_id === groupId)
  }

  return { me, hasAccess, isGovernance, detecting, detectFailed, detect, workspaceForGroup }
}
