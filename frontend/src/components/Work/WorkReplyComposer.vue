<script setup>
// 回复输入器（§7/§7.5）：纯文本回复；服务端成功保存才算发出（失败保留草稿可重试）；
// client_request_id 幂等（网络重试不产生重复回复）。可选「需要某人回应」生成待回复。
import { ref, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { DewButton } from '@bme/dew-ui'
import { workService } from '../../services/workService'
import { newClientRequestId } from '../../composables/useWorkData'

const props = defineProps({
  itemId: { type: Number, required: true },
  // 本事项可被指定回应的候选人（有读取权的参与者/作者，由父组件传入）
  responders: { type: Array, default: () => [] },
  replyTo: { type: Object, default: null },
  // 该用户在此事项的待回应请求（回复时自动完结）
  pendingRequest: { type: Object, default: null },
})
const emit = defineEmits(['sent'])

const body = ref('')
const sending = ref(false)
const needReply = ref(false)
const responseForm = reactive({ userId: null, dueAt: null })

const canSend = computed(() => body.value.trim().length > 0 && !sending.value)

async function send() {
  if (!canSend.value) return
  sending.value = true
  try {
    const payload = {
      body: body.value.trim(),
      client_request_id: newClientRequestId(),
    }
    if (props.replyTo) payload.reply_to_id = props.replyTo.id
    if (props.pendingRequest) payload.response_to_request_id = props.pendingRequest.request_id
    if (needReply.value && responseForm.userId) {
      payload.response = { user_id: responseForm.userId }
      if (responseForm.dueAt) payload.response.due_at = responseForm.dueAt
    }
    const res = await workService.sendReply(props.itemId, payload)
    body.value = ''
    needReply.value = false
    responseForm.userId = null
    responseForm.dueAt = null
    ElMessage.success('已发送')
    emit('sent', { id: res.data?.id, seq: res.data?.seq })
  } catch (e) {
    // 失败保留输入内容（发送中/失败可重试态，§6.2）
    ElMessage.error(e.response?.data?.message || '发送失败，内容已保留，请重试')
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <div class="composer">
    <div v-if="replyTo" class="reply-quote">
      回复 {{ replyTo.author_name }}：{{ (replyTo.body || '').slice(0, 40) }}…
      <DewButton type="ghost" size="sm" class="quote-cancel" @click="$emit('cancel-quote')">取消引用</DewButton>
    </div>
    <div v-if="pendingRequest" class="reply-quote reply-quote--hot">
      这条回复将完结「{{ pendingRequest.item_title }}」的待回应请求
    </div>
    <el-input v-model="body" type="textarea" :rows="3" maxlength="5000"
              placeholder="补充进展、说明阻碍或回复他人（纯文本，换行保留）" />
    <div class="composer-actions">
      <template v-if="responders.length">
        <DewButton v-if="!needReply" type="ghost" size="sm" @click="needReply = true">
          需要某人回应
        </DewButton>
        <template v-else>
          <el-select v-model="responseForm.userId" size="small" style="width: 140px;"
                     placeholder="选择回应人">
            <el-option v-for="r in responders" :key="r.user_id" :label="r.username"
                       :value="r.user_id" />
          </el-select>
          <el-date-picker v-model="responseForm.dueAt" size="small" type="datetime"
                          placeholder="建议回复时限（可选）" value-format="YYYY-MM-DDTHH:mm"
                          style="width: 200px;" />
          <DewButton type="ghost" size="sm"
                     @click="needReply = false; responseForm.userId = null">取消</DewButton>
        </template>
      </template>
      <div class="spacer" />
      <span class="char-hint">{{ body.length }}/5000</span>
      <DewButton size="sm" active :loading="sending" :disabled="!canSend" @click="send">
        发送
      </DewButton>
    </div>
  </div>
</template>

<style scoped>
.composer { margin-top: 12px; }

/* 底色用 Dew token：暗色自动翻转（EP 仅亮色 token 会在暗色下刺眼） */
.reply-quote {
  display: flex; align-items: center; gap: 6px;
  margin-bottom: 8px; padding: 8px 12px; border-radius: 8px;
  font-size: 12.5px; color: var(--dew-text-muted);
  background: var(--dew-card-flat-bg);
}
.reply-quote--hot {
  color: var(--el-color-warning, #e6a23c);
  background: var(--color-warning-light);
}
.quote-cancel { flex: none; }

.composer-actions {
  display: flex; align-items: center; gap: 8px; margin-top: 8px; flex-wrap: wrap;
}
.spacer { flex: 1; }
.char-hint { font-size: 12px; color: var(--dew-text-muted); font-variant-numeric: tabular-nums; }
</style>
