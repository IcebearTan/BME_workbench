<template>
  <div class="dew-sidebar__node">
    <button
      type="button"
      class="dew-sidebar__item"
      :class="{
        'is-active': isActive,
        'is-disabled': node.disabled,
        'is-group': hasChildren,
      }"
      :style="{ '--depth': depth }"
      :disabled="node.disabled"
      @click="handleClick"
    >
      <span
        v-if="hasChildren && collapsible"
        class="dew-sidebar__arrow"
        :class="{ 'is-expanded': expanded }"
      >
        <el-icon><ArrowRight /></el-icon>
      </span>
      <span v-else class="dew-sidebar__arrow dew-sidebar__arrow--placeholder" />
      <el-icon v-if="node.icon" class="dew-sidebar__icon">
        <component :is="node.icon" />
      </el-icon>
      <span class="dew-sidebar__label">{{ node.label }}</span>
    </button>

    <div v-if="hasChildren" class="dew-sidebar__children" :class="{ 'is-collapsed': !expanded }">
      <div class="dew-sidebar__children-inner">
        <DewSidebarNode
          v-for="child in node.children"
          :key="[...myPath, child.value ?? child.label].join('/')"
          :node="child"
          :depth="depth + 1"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, inject, provide } from 'vue'
import { ArrowRight } from '@element-plus/icons-vue'

// 递归节点：靠 name 自引用渲染任意层级子节点
defineOptions({ name: 'DewSidebarNode' })

const props = defineProps({
  node: { type: Object, required: true },
  depth: { type: Number, default: 0 },
})

const ctx = inject('dew-sidebar')
// 父节点下发的祖先路径链（selfKey 序列），根节点默认空
const parentNav = inject('dew-sidebar-nav', { path: [] })

const hasChildren = computed(() => Array.isArray(props.node.children) && props.node.children.length > 0)
const collapsible = computed(() => ctx.props.collapsible)

// 唯一 key：祖先路径拼接，避免同名节点冲突
const selfKey = props.node.value ?? props.node.label
const myPath = [...parentNav.path, selfKey]
const nodeKey = myPath.join('/')
// 祖先的路径 key（accordion 展开时需保留父链）
const ancestorKeys = parentNav.path.map((_, i) => parentNav.path.slice(0, i + 1).join('/'))

// 把自己的路径下发给子节点（递归传递，让深层节点能算出完整路径）
provide('dew-sidebar-nav', { path: myPath })

// collapsible=false 时视为始终展开
const expanded = computed(() => !collapsible.value || ctx.state.expanded.has(nodeKey))
const isActive = computed(
  () => !hasChildren.value && props.node.value !== undefined && ctx.state.active === props.node.value
)

function handleClick() {
  if (props.node.disabled) return
  if (hasChildren.value) {
    if (collapsible.value) ctx.toggleExpand(nodeKey, ancestorKeys)
    // 不可折叠模式：分组点击无操作
  } else if (props.node.value !== undefined) {
    ctx.select(props.node.value, props.node)
  }
}
</script>
