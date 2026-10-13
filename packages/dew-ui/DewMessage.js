/**
 * DewMessage — 命令式消息气泡（toast）
 *
 * 用法：
 *   DewMessage.success('保存成功')
 *   DewMessage.warning('请填写完整')
 *   DewMessage.error('提交失败，请重试')
 *   DewMessage.info('这是一条普通提示')
 *   DewMessage.success('5 秒后消失', 5000)   // 自定义时长
 *   DewMessage.info('需手动关闭', 0)         // duration=0 不自动关
 *   const id = DewMessage.success(...)        // 返回 id
 *   DewMessage.close(id)                      // 关指定
 *   DewMessage.closeAll()                     // 关全部
 *
 * 实现：单例容器（首次调用 ensure 挂到 body）+ reactive 队列 + TransitionGroup 堆叠。
 * API 对齐 ElMessage，方便逐步替代。
 */
import { createApp, h, reactive } from 'vue'
import { ElIcon } from 'element-plus'
import DewMessageContainer from './DewMessage.vue'

const toasts = reactive([])
let app = null
let seq = 0

function ensure() {
  if (app) return
  app = createApp({
    render: () => h(DewMessageContainer, { toasts, onClose: remove }),
  })
  // DewMessageContainer 内部用了 <el-icon>，动态 app 需注册
  app.component('ElIcon', ElIcon)
  const container = document.createElement('div')
  container.className = 'dew-message-root'
  document.body.appendChild(container)
  app.mount(container)
}

function remove(id) {
  const i = toasts.findIndex((t) => t.id === id)
  if (i >= 0) toasts.splice(i, 1)
}

function show(type, text, duration = 3000) {
  ensure()
  const id = ++seq
  toasts.push({ id, type, text })
  if (duration > 0) {
    setTimeout(() => remove(id), duration)
  }
  return id
}

export const DewMessage = {
  success(text, duration) { return show('success', text, duration) },
  warning(text, duration) { return show('warning', text, duration) },
  error(text, duration)   { return show('error', text, duration) },
  info(text, duration)    { return show('info', text, duration) },
  close: remove,
  closeAll() { toasts.splice(0, toasts.length) },
}

export default DewMessage
