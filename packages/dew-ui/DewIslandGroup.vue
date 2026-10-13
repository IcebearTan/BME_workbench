<template>
  <div class="island-group">
    <!-- 主岛（可展开） -->
    <DewIsland
      v-if="$slots['main-trigger']"
      :model-value="openKey === 'main'"
      :panel-width="mainPanelWidth"
      @update:model-value="(v) => onToggle('main', v)"
    >
      <template #trigger><slot name="main-trigger" /></template>
      <slot name="main-content" />
    </DewIsland>

    <!-- 卫星岛（可展开，极简彩色胶囊） -->
    <div v-if="items && items.length" class="island-group__sats">
      <DewIsland
        v-for="(item, i) in items"
        :key="i"
        :model-value="openKey === i"
        :panel-width="satPanelWidth"
        @update:model-value="(v) => onToggle(i, v)"
      >
        <template #trigger>
          <div class="sat-pill" :style="pillStyle(item)">
            <span class="sat-pill__value" :style="{ color: item.color }">{{ item.value }}</span>
            <span v-if="item.unit" class="sat-pill__unit" :style="{ color: item.color }">{{ item.unit }}</span>
          </div>
        </template>
        <slot name="detail" :item="item" :index="i" />
      </DewIsland>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import DewIsland from './DewIsland.vue'

const props = defineProps({
  /** 卫星岛触发数据：[{ value, unit?, color?(hex), ... }]；其余字段透传给 #detail 插槽 */
  items: { type: Array, default: () => [] },
  /** 主岛/卫星岛展开面板宽度 */
  mainPanelWidth: { type: [String, Number], default: 300 },
  satPanelWidth: { type: [String, Number], default: 240 },
})

// 统一展开状态：null | 'main' | 卫星岛 index —— 主岛与卫星岛互斥，同时只开一个
const openKey = ref(null)
function onToggle(key, v) {
  openKey.value = v ? key : null
}

function pillStyle(item) {
  const c = item.color
  return {
    // 彩色渐变淡彩底（无 backdrop-filter，省性能；靠 inset 高光做出玻璃卡片感）
    background: c
      ? `linear-gradient(135deg, ${c}33, ${c}14)`
      : 'linear-gradient(135deg, rgba(127,127,127,0.14), rgba(127,127,127,0.06))',
    borderColor: c ? `${c}40` : 'rgba(127,127,127,0.16)',
  }
}
</script>

<style scoped>
.island-group {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  font-family: var(--dew-font, inherit);
}

.island-group__sats {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

/* 卫星岛触发器：极简彩色胶囊，与主岛等高 50px、pill 圆角 */
.sat-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 2px;
  height: 50px;
  padding: 0 20px;
  border-radius: 9999px;
  border: 1px solid;
  box-shadow:
    0 2px 10px rgba(0, 0, 0, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.45);
  cursor: pointer;
  font-family: var(--dew-font, inherit);
  transition: transform 0.3s var(--dew-bounce), box-shadow 0.3s ease;
}

.sat-pill:hover {
  transform: translateY(-2px);
  box-shadow:
    0 6px 18px rgba(0, 0, 0, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.55);
}

.sat-pill__value {
  font-size: 20px;
  font-weight: 800;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

.sat-pill__unit {
  font-size: 12px;
  font-weight: 700;
  opacity: 0.85;
}
</style>
