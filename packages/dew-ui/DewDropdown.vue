<template>
  <DewPopover
    v-model="visible"
    :trigger="trigger"
    :placement="placement"
    :show-arrow="false"
    :offset="4"
    :disabled="disabled"
  >
    <template #trigger>
      <slot name="trigger" />
    </template>

    <div class="dew-dropdown" :style="dropdownStyle">
      <div
        v-for="(item, index) in items"
        :key="index"
        class="dew-dropdown__item"
        :class="{ 'dew-dropdown__item--danger': item.danger, 'dew-dropdown__item--disabled': item.disabled }"
        @click="onSelect(item)"
      >
        <component v-if="item.icon" :is="item.icon" class="dew-dropdown__icon" />
        <span class="dew-dropdown__label">{{ item.label }}</span>
      </div>
    </div>
  </DewPopover>
</template>

<script setup>
import { computed } from 'vue'
import DewPopover from './DewPopover.vue'

const props = defineProps({
  /** v-model 控制显隐 */
  modelValue: { type: Boolean, default: false },
  /** 触发方式 click | hover */
  trigger: { type: String, default: 'click' },
  /** 弹出位置 bottom | top */
  placement: { type: String, default: 'bottom' },
  /** 菜单项 [{ label, icon?, command, danger?, disabled? }] */
  items: { type: Array, default: () => [] },
  /** 禁用 */
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'select'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const dropdownStyle = computed(() => ({
  minWidth: '120px',
}))

function onSelect(item) {
  if (item.disabled) return
  emit('select', item.command ?? item.label)
  visible.value = false
}
</script>

<style scoped>
.dew-dropdown {
  padding: 4px;
}

.dew-dropdown__item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 450;
  color: var(--dew-popover-text);
  white-space: nowrap;
  transition: background 0.15s ease;
}

.dew-dropdown__item:hover {
  background: var(--dew-popover-item-hover);
}

.dew-dropdown__item--danger {
  color: var(--color-danger);
}

.dew-dropdown__item--danger:hover {
  background: rgba(239, 68, 68, 0.08);
}

.dew-dropdown__item--disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.dew-dropdown__icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.dew-dropdown__label {
  line-height: 1;
}
</style>
