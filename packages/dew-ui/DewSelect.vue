<template>
  <div class="dew-select" :class="{ 'dew-select--disabled': disabled }">
    <DewPopover v-model="open" placement="bottom" :offset="6" :disabled="disabled">
      <template #trigger>
        <div ref="triggerRef" class="dew-select__trigger"
          :class="[`dew-select--${size}`, { 'dew-select__trigger--open': open }]" role="combobox">
          <span class="dew-select__value" :class="{ 'is-placeholder': !displayLabel }">
            {{ displayLabel || placeholder }}
          </span>
          <svg class="dew-select__chevron" :class="{ 'is-open': open }" viewBox="0 0 16 16" width="14" height="14" fill="currentColor">
            <path d="M8 11L3 6h10z" />
          </svg>
        </div>
      </template>
      <div class="dew-select__dropdown" :style="{ minWidth: triggerWidth + 'px' }">
        <input v-if="filterable" v-model="query" class="dew-select__filter" placeholder="搜索…" />
        <div class="dew-select__options">
          <div v-for="opt in filteredOptions" :key="opt.value"
            :class="['dew-select__option', { 'is-selected': opt.value === modelValue }]"
            @click="select(opt)">
            <span>{{ opt.label }}</span>
            <svg v-if="opt.value === modelValue" class="dew-select__check" viewBox="0 0 16 16" width="14" height="14" fill="currentColor">
              <path d="M13.485 4.515a.5.5 0 0 1 0 .707l-6.5 6.5a.5.5 0 0 1-.707 0l-3.5-3.5a.5.5 0 1 1 .707-.707L6.5 10.793l6.278-6.278a.5.5 0 0 1 .707 0z" />
            </svg>
          </div>
          <div v-if="!filteredOptions.length" class="dew-select__empty">无匹配项</div>
        </div>
      </div>
    </DewPopover>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue';
import DewPopover from './DewPopover.vue';

const props = defineProps({
  /** v-model 选中值 */
  modelValue: { type: [String, Number, null], default: null },
  /** 选项 [{label, value}] */
  options: { type: Array, required: true },
  placeholder: { type: String, default: '请选择' },
  /** sm | md | lg（对齐 DewInput） */
  size: { type: String, default: 'md' },
  filterable: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
});
const emit = defineEmits(['update:modelValue', 'change']);

const open = ref(false);
const query = ref('');
const triggerRef = ref(null);
const triggerWidth = ref(0);

const displayLabel = computed(() => {
  const opt = props.options.find((o) => o.value === props.modelValue);
  return opt ? opt.label : '';
});

const filteredOptions = computed(() => {
  if (!props.filterable || !query.value) return props.options;
  const q = String(query.value).toLowerCase();
  return props.options.filter((o) => String(o.label).toLowerCase().includes(q));
});

function select(opt) {
  emit('update:modelValue', opt.value);
  emit('change', opt);
  open.value = false;
  query.value = '';
}

// 展开时测算触发器宽度，让浮层至少与触发器同宽
watch(open, (v) => {
  if (v) {
    query.value = '';
    nextTick(() => {
      if (triggerRef.value) triggerWidth.value = triggerRef.value.getBoundingClientRect().width;
    });
  }
});
</script>

<style scoped>
.dew-select { width: 100%; display: block; }
/* 让 DewPopover 的触发器容器撑满 */
.dew-select :deep(.dew-popover-wrapper) { width: 100%; display: block; }
.dew-select :deep(.dew-popover__trigger) { width: 100%; display: block; }

/* ── 触发器（液态玻璃，复用 --dew-input-* 变量，与 DewInput 一致） ── */
.dew-select__trigger {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  backdrop-filter: blur(20px) saturate(1.5);
  -webkit-backdrop-filter: blur(20px) saturate(1.5);
  background: var(--dew-input-bg);
  border: 1px solid var(--dew-input-border);
  box-shadow: var(--dew-input-shadow);
  cursor: pointer;
  font-family: var(--dew-font, inherit);
  transition: background .35s var(--dew-bounce), border-color .35s var(--dew-bounce), box-shadow .35s var(--dew-bounce);
}
.dew-select__trigger:hover { background: var(--dew-input-bg-hover); }
.dew-select__trigger--open {
  background: var(--dew-input-bg-focus);
  border-color: var(--dew-input-border-focus);
  box-shadow: var(--dew-input-shadow-focus);
}

/* 尺寸（与 DewInput 一致） */
.dew-select--sm { height: 32px; border-radius: 10px; }
.dew-select--sm .dew-select__value { font-size: 12px; padding: 0 6px 0 10px; }
.dew-select--md { height: 40px; border-radius: 12px; }
.dew-select--md .dew-select__value { font-size: 14px; padding: 0 8px 0 12px; }
.dew-select--lg { height: 48px; border-radius: 14px; }
.dew-select--lg .dew-select__value { font-size: 15px; padding: 0 10px 0 14px; }

.dew-select__value {
  flex: 1;
  color: var(--dew-input-text);
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.dew-select__value.is-placeholder { color: var(--dew-input-placeholder); font-weight: 400; }

.dew-select__chevron {
  flex-shrink: 0;
  margin-right: 10px;
  color: var(--dew-input-placeholder);
  transition: transform .3s var(--dew-bounce), color .3s;
}
.dew-select__trigger--open .dew-select__chevron { transform: rotate(180deg); color: var(--dew-input-text); }

.dew-select--disabled .dew-select__trigger { cursor: not-allowed; opacity: .5; }

/* ── 浮层内容（浮层本体 iOS 纯色由 DewPopover 提供） ── */
.dew-select__dropdown { padding: 6px; max-height: 280px; overflow-y: auto; box-sizing: border-box; }
.dew-select__filter {
  width: 100%;
  box-sizing: border-box;
  padding: 6px 10px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  font-size: 13px;
  color: var(--dew-text);
  background: var(--color-bg-soft);
  outline: none;
  margin-bottom: 6px;
  font-family: inherit;
}
.dew-select__filter:focus { border-color: var(--color-primary); }

.dew-select__options { display: flex; flex-direction: column; gap: 2px; }
.dew-select__option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 14px;
  color: var(--dew-popover-text, var(--dew-text));
  cursor: pointer;
  transition: background .15s ease, color .15s ease;
}
.dew-select__option:hover { background: var(--dew-ghost-hover-bg); }
.dew-select__option.is-selected { color: var(--color-primary); font-weight: 600; }
.dew-select__check { flex-shrink: 0; color: var(--color-primary); }
.dew-select__empty { padding: 16px; text-align: center; font-size: 13px; color: var(--dew-text-faint); }
</style>
