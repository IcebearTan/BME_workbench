<template>
  <nav class="dew-sidebar" :class="[`dew-sidebar--${size}`, { 'dew-sidebar--glass': glass }]">
    <DewSidebarNode
      v-for="item in items"
      :key="item.value ?? item.label"
      :node="item"
      :depth="0"
    />
  </nav>
</template>

<script setup>
import { provide, reactive, watch, onMounted } from 'vue'
import DewSidebarNode from './DewSidebarNode.vue'

const props = defineProps({
  /** 树形数据：[{ value?, label, icon?, children?, disabled? }]，有 children 即可折叠分组 */
  items: { type: Array, required: true },
  /** 当前激活项的 value（v-model） */
  modelValue: { type: [String, Number], default: null },
  /** 是否允许折叠分组（false = 固定侧边栏，全展开） */
  collapsible: { type: Boolean, default: true },
  /** 手风琴：展开一个自动收起其他 */
  accordion: { type: Boolean, default: false },
  /** 默认全部展开（仅 collapsible 时生效） */
  defaultExpandAll: { type: Boolean, default: true },
  /** 或指定默认展开的 value/label 列表 */
  defaultExpanded: { type: Array, default: () => [] },
  /** 容器玻璃质感 */
  glass: { type: Boolean, default: false },
  /** 尺寸：sm/md/lg，影响项高度、内边距、字号、缩进步进 */
  size: { type: String, default: 'md', validator: (v) => ['sm', 'md', 'lg'].includes(v) },
})

const emit = defineEmits(['update:modelValue', 'select'])

const getSelfKey = (node) => node.value ?? node.label

const state = reactive({
  active: props.modelValue,
  expanded: new Set(),
})

// 外部 modelValue 变化时同步进来
watch(() => props.modelValue, (v) => { state.active = v })

// 收集所有分组节点的「路径 key」（祖先链拼接，保证同名节点也不冲突）
function collectGroupKeys(nodes) {
  const keys = []
  const walk = (list, parentPath) => {
    for (const n of list) {
      const path = [...parentPath, getSelfKey(n)]
      if (Array.isArray(n.children) && n.children.length) {
        keys.push(path.join('/'))
        walk(n.children, path)
      }
    }
  }
  walk(nodes, [])
  return keys
}

// defaultExpanded 按 selfKey(label/value) 匹配，返回对应路径 key
function keysBySelfKey(nodes, matchSet) {
  const keys = []
  const walk = (list, parentPath) => {
    for (const n of list) {
      const path = [...parentPath, getSelfKey(n)]
      if (Array.isArray(n.children) && n.children.length) {
        if (matchSet.has(getSelfKey(n))) keys.push(path.join('/'))
        walk(n.children, path)
      }
    }
  }
  walk(nodes, [])
  return keys
}

function initExpanded() {
  state.expanded = new Set()
  if (!props.collapsible) return
  if (props.defaultExpandAll) {
    collectGroupKeys(props.items).forEach((k) => state.expanded.add(k))
  } else {
    const matchSet = new Set(props.defaultExpanded)
    keysBySelfKey(props.items, matchSet).forEach((k) => state.expanded.add(k))
  }
}
onMounted(initExpanded)

provide('dew-sidebar', {
  state,
  props,
  select(value, node) {
    state.active = value
    emit('update:modelValue', value)
    emit('select', value, node)
  },
  // ancestors = 当前节点的祖先路径 key 列表，accordion 展开时需保留父链可见
  toggleExpand(key, ancestors = []) {
    if (!props.collapsible) return
    if (props.accordion) {
      // 手风琴：展开「当前 + 祖先」，同级兄弟不在其中自然折叠；再点已展开项则收起当前
      state.expanded = state.expanded.has(key) ? new Set(ancestors) : new Set([...ancestors, key])
    } else {
      const next = new Set(state.expanded)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      state.expanded = next
    }
  },
})
</script>

<style>
.dew-sidebar {
  --dew-sidebar-pad-y: 7px;
  --dew-sidebar-pad-x: 10px;
  --dew-sidebar-font: 13px;
  --dew-sidebar-indent: 14px;
  width: 100%;
  font-family: var(--dew-font, inherit);
  font-size: var(--dew-sidebar-font);
}
.dew-sidebar--sm {
  --dew-sidebar-pad-y: 4px;
  --dew-sidebar-pad-x: 9px;
  --dew-sidebar-font: 12px;
  --dew-sidebar-indent: 12px;
}
.dew-sidebar--lg {
  --dew-sidebar-pad-y: 10px;
  --dew-sidebar-pad-x: 12px;
  --dew-sidebar-font: 14px;
  --dew-sidebar-indent: 16px;
}
.dew-sidebar--glass {
  background: rgba(255, 255, 255, 0.55);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 0.5px solid rgba(255, 255, 255, 0.6);
  border-radius: 14px;
  padding: 10px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06), inset 0 1px 0 rgba(255, 255, 255, 0.6);
}

.dew-sidebar__item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  text-align: left;
  border: none;
  background: transparent;
  cursor: pointer;
  font-family: inherit;
  font-size: var(--dew-sidebar-font);
  color: var(--dew-text-muted);
  padding-top: var(--dew-sidebar-pad-y);
  padding-bottom: var(--dew-sidebar-pad-y);
  padding-right: var(--dew-sidebar-pad-x);
  padding-left: calc(var(--dew-sidebar-pad-x) + var(--depth, 0) * var(--dew-sidebar-indent));
  border-radius: 8px;
  margin-bottom: 2px;
  transition: background 0.15s, color 0.15s;
}
.dew-sidebar__item:hover:not(.is-disabled) {
  background: rgba(127, 127, 127, 0.08);
  color: var(--dew-text-heading);
}
.dew-sidebar__item.is-active {
  background: rgba(255, 255, 255, 0.6);
  color: var(--dew-text-heading);
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05), inset 0 1px 0 rgba(255, 255, 255, 0.7);
}
/* glass 模式：容器本身已是液态玻璃，选中改用淡色标记（避免叠两层玻璃糊掉） */
.dew-sidebar--glass .dew-sidebar__item.is-active {
  background: rgba(255, 255, 255, 0.32);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.4);
}
.dew-sidebar__item.is-disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
/* 分组标题样式：有 children 的节点 */
.dew-sidebar__item.is-group {
  font-size: 11px;
  font-weight: 600;
  color: var(--dew-text-faint);
  letter-spacing: 0.4px;
  text-transform: uppercase;
  margin-top: 6px;
}
.dew-sidebar__item.is-group:hover:not(.is-disabled) {
  background: rgba(127, 127, 127, 0.06);
  color: var(--dew-text-muted);
}
.dew-sidebar__item.is-group:first-child {
  margin-top: 0;
}

.dew-sidebar__arrow {
  display: inline-flex;
  width: 14px;
  height: 14px;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--dew-text-faint);
  transition: transform 0.25s var(--dew-bounce, cubic-bezier(0.34, 1.56, 0.64, 1));
}
.dew-sidebar__arrow .el-icon { font-size: 12px; }
.dew-sidebar__arrow.is-expanded { transform: rotate(90deg); }
.dew-sidebar__arrow--placeholder { visibility: hidden; }

.dew-sidebar__icon {
  font-size: 15px;
  flex-shrink: 0;
  color: inherit;
}
.dew-sidebar__label {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 子节点折叠：grid 0fr→1fr 高度过渡（纯 CSS，无需 JS 量高度） */
.dew-sidebar__children {
  display: grid;
  grid-template-rows: 1fr;
  transition: grid-template-rows 0.28s ease;
}
.dew-sidebar__children.is-collapsed {
  grid-template-rows: 0fr;
}
.dew-sidebar__children-inner {
  min-height: 0;
  overflow: hidden;
}

/* 暗色模式 */
.theme-dark .dew-sidebar__item:hover:not(.is-disabled) {
  background: rgba(255, 255, 255, 0.06);
}
.theme-dark .dew-sidebar__item.is-active {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.95);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08);
}
.theme-dark .dew-sidebar--glass .dew-sidebar__item.is-active {
  background: rgba(255, 255, 255, 0.14);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.1);
}
.theme-dark .dew-sidebar--glass {
  background: rgba(40, 40, 48, 0.6);
  border-color: rgba(255, 255, 255, 0.1);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.06);
}
</style>
