/**
 * DewMessageBox — 命令式弹窗（函数调用 → Promise）
 *
 * 用法：
 *   await DewMessageBox.confirm('确定删除？', '删除确认')
 *   await DewMessageBox.alert('保存成功', '提示')
 *
 * confirm：点「确认」→ resolve；点「取消」/关/X → reject('cancel')
 * alert：任何关闭方式 → resolve
 */
import { createApp, h, reactive } from 'vue'
import { ElIcon } from 'element-plus'
import DewDialog from './DewDialog.vue'
import DewButton from './DewButton.vue'

function mountDialog({ message, title, confirmText, cancelText, isAlert, width }) {
  return new Promise((resolve, reject) => {
    const state = reactive({ visible: true })

    function done(action) {
      state.visible = false
      // 等离场动画结束再卸载（0.2s 过渡 + 余量）
      setTimeout(() => {
        app.unmount()
        container.remove()
      }, 300)
      if (action === 'confirm' || isAlert) resolve()
      else reject(action || 'cancel')
    }

    const app = createApp({
      render() {
        return h(
          DewDialog,
          {
            modelValue: state.visible,
            'onUpdate:modelValue': (v) => {
              if (!v) done(isAlert ? 'confirm' : 'cancel')
            },
            title,
            width,
          },
          {
            default: () => message,
            footer: () => [
              !isAlert &&
                h(DewButton, { onClick: () => done('cancel') }, () => cancelText),
              h(DewButton, { active: true, onClick: () => done('confirm') }, () => confirmText),
            ].filter(Boolean),
          }
        )
      },
    })
    // DewDialog 内部用了 <el-icon>，动态 app 需注册
    app.component('ElIcon', ElIcon)

    const container = document.createElement('div')
    document.body.appendChild(container)
    app.mount(container)
  })
}

export const DewMessageBox = {
  /**
   * 确认框：resolve = 确认，reject = 取消/关闭
   * @param {string} message 消息内容
   * @param {string} [title='提示'] 标题
   * @param {object} [options] { confirmText, cancelText, width }
   */
  confirm(message, title = '提示', options = {}) {
    return mountDialog({
      message,
      title,
      confirmText: options.confirmText || '确认',
      cancelText: options.cancelText || '取消',
      isAlert: false,
      width: options.width || 420,
    })
  },

  /**
   * 提示框：任何关闭方式都 resolve
   */
  alert(message, title = '提示', options = {}) {
    return mountDialog({
      message,
      title,
      confirmText: options.confirmText || '确定',
      cancelText: null,
      isAlert: true,
      width: options.width || 420,
    })
  },
}

export default DewMessageBox
