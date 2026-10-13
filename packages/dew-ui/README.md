# Dew UI 组件库

基于 Vue 3 的液态玻璃风格组件库。露珠般的晶莹、毛玻璃折射、柔和阴影、水滴弹性过渡。

## 快速开始

```js
import { DewButton, DewButtonBar, DewCard, DewBadge, DewTag } from '@/components/ui'
```

---

## DewButton 按钮

液态玻璃按钮，支持鼠标追踪折射、弹性宽度过渡、可切换点亮状态。

### Props

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `type` | `string` | `'glass'` | 按钮类型：`glass` / `danger` / `ghost` |
| `size` | `string` | `'md'` | 尺寸：`sm` / `md` / `lg` |
| `active` | `boolean` | `false` | 点亮状态，可交互切换 |
| `disabled` | `boolean` | `false` | 禁用 |
| `block` | `boolean` | `false` | 撑满父容器宽度 |

### Events

| 事件 | 参数 | 说明 |
|------|------|------|
| `click` | `Event` | 点击事件 |

### 使用示例

```vue
<template>
  <DewButton>确定</DewButton>
  <DewButton type="danger">删除</DewButton>
  <DewButton type="ghost">取消</DewButton>
  <DewButton :active="isOn" @click="isOn = !isOn">
    {{ isOn ? '已关注' : '关注' }}
  </DewButton>
</template>

<script setup>
import { ref } from 'vue'
import { DewButton } from '@/components/ui'
const isOn = ref(false)
</script>
```

### 视觉特性

- **鼠标追踪折射**：悬停时折射光和色散彩虹跟随鼠标实时变化
- **弹性宽度过渡**：内容变化时以水滴弹性曲线平滑变形
- **点亮状态**：`glass` 白光充盈，`danger` 红色光焰

---

## DewButtonBar 按钮栏

分段选择器，支持滑动指示器、图标、未读计数。

### Props

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `items` | `Array` | — | 选项列表 `[{ value, label, icon?, badge? }]` |
| `modelValue` | `string/number` | `null` | 当前选中值（v-model） |
| `size` | `string` | `'md'` | 尺寸：`sm` / `md` / `lg` |

---

## DewCard 卡片

圆角卡片容器，支持多种变体、毛玻璃、色彩底色和可交互模式。

### Props

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `variant` | `string` | `'default'` | 卡片变体：`default` / `elevated` / `inset` |
| `size` | `string` | `'md'` | 尺寸：`sm` / `md` / `lg`（控制内边距） |
| `glass` | `boolean` | `false` | 增强毛玻璃效果 |
| `interactive` | `boolean` | `false` | 可交互，带点击反馈 |
| `noHover` | `boolean` | `false` | 禁用悬停上浮效果 |
| `tinted` | `boolean` | `false` | 色彩底色模式 |
| `accent` | `string` | `null` | 强调色：`primary` / `success` / `warning` / `danger` / `info` |
| `divided` | `boolean` | `false` | 显示 header 底部分割线 |

### Events

| 事件 | 参数 | 说明 |
|------|------|------|
| `click` | `Event` | 点击事件（`interactive` 模式下触发） |

### Slots

| 插槽 | 说明 |
|------|------|
| `header` | 卡片头部 |
| `default` | 卡片内容 |
| `footer` | 卡片底部 |

### 使用示例

```vue
<template>
  <DewCard>
    <template #header>标题</template>
    <p>卡片内容</p>
    <template #footer>
      <DewButton size="sm">确认</DewButton>
    </template>
  </DewCard>

  <DewCard variant="elevated">浮起</DewCard>
  <DewCard variant="inset">凹陷</DewCard>
  <DewCard :glass="true">毛玻璃</DewCard>
  <DewCard :tinted="true" accent="primary" :glass="true">色彩底色</DewCard>
  <DewCard :interactive="true" @click="handleClick">可点击</DewCard>
</template>

<script setup>
import { DewCard, DewButton } from '@/components/ui'
</script>
```

### 视觉特性

- **鼠标追踪折射**：折射光和色散彩虹跟随鼠标
- **弹性上浮**：水滴弹性曲线 hover 上浮
- **顶部高光线**：模拟玻璃边缘高光
- **色彩底色**：`tinted` + `glass` 叠加淡色渐变

---

## DewIsland 浮岛

液态玻璃「灵动岛」容器：收起态展示触发器（如胶囊），点击展开成居中浮层面板，常用于实时状态浓缩 → 展开详情（如打卡时长 → 自习室实况）。

### Props

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `modelValue` | `boolean` | `false` | 展开/收起（v-model） |
| `disabled` | `boolean` | `false` | 禁用点击展开 |
| `panelWidth` | `string / number` | `360` | 面板宽度（number → px；string 原样使用，如 `'min(360px, calc(100vw - 24px))'`） |
| `margin` | `number` | `12` | 视口边缘留白（px），用于定位钳制 |

### Events

| 事件 | 参数 | 说明 |
|------|------|------|
| `update:modelValue` | `boolean` | v-model 同步 |

### Slots

| 插槽 | 说明 |
|------|------|
| `trigger` | 触发器（收起态展示，点击切换） |
| default | 展开态面板内容 |

### 使用示例

```vue
<template>
  <DewIsland v-model="open" :panel-width="360">
    <template #trigger>
      <DewButton size="lg">学习中 02:15:33</DewButton>
    </template>
    <div style="height: 300px;">面板内容</div>
  </DewIsland>
</template>
```

### 视觉特性

- **液态玻璃浮岛**：`backdrop-filter` 模糊 + 玻璃 bg/border/shadow token（`--dew-island-*`）
- **水滴绽放动画**：`--dew-bounce` 弹性曲线，`transform-origin: top center`，从触发器顶部向下绽放
- **点击外部收起**：document capture 监听，无遮罩、不阻断背景交互
- **跟随触发器定位**：水平居中于触发器，滚动/resize 自动重定位

---

## DewBadge 徽标

数字或文字徽标，用于状态标记和未读计数。

### Props

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `value` | `number / string` | `null` | 显示的数值或文字 |
| `type` | `string` | `'primary'` | 颜色类型：`primary` / `success` / `warning` / `danger` / `info` / `neutral` |

---

## DewTag 标签

分类标签，用于标记类型、状态等。

### Props

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `type` | `string` | `'primary'` | 颜色类型：`primary` / `success` / `warning` / `danger` / `info` / `neutral` |
| `size` | `string` | `'md'` | 尺寸：`sm` / `md` |
| `round` | `boolean` | `false` | 完全圆角（药丸形） |

---

## DewInput 输入框

液态玻璃输入框，支持鼠标追踪折射、聚焦发光、密码切换、清除按钮、IME 中文输入兼容、el-form-item 自动感知错误态。

### Props

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `modelValue` | `string` | `''` | 输入值（v-model） |
| `type` | `string` | `'text'` | `text` / `email` / `password` |
| `size` | `string` | `'md'` | 尺寸：`sm` / `md` / `lg` |
| `clearable` | `boolean` | `false` | 显示清除按钮 |
| `disabled` | `boolean` | `false` | 禁用 |
| `error` | `boolean` | `false` | 错误态（红色描边） |
| `round` | `boolean` | `false` | 全圆角（搜索框风格） |
| `expandOnFocus` | `boolean` | `false` | 聚焦时展开宽度 |
| `prefixIcon` / `suffixIcon` | `component` | `null` | 前/后缀图标 |

> 与 el-form 配合需加 `novalidate` 禁用浏览器原生验证；:invalid 红色虚线需在 main.css 全局重置。

---

## DewSwitch 开关

液态玻璃开关，水滴弹性滑动 + 胶囊形 thumb（thumb 宽超轨道 50%，胖胶囊风格）。

### Props

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `modelValue` | `boolean` | `false` | 开关状态（v-model） |
| `disabled` | `boolean` | `false` | 禁用 |
| `size` | `string` | `'md'` | `md`（轨道 44×24）/ `sm`（36×20） |
| `activeColor` | `string` | `null` | 自定义激活色 |

### Events

| 事件 | 参数 | 说明 |
|------|------|------|
| `update:modelValue` | `boolean` | v-model 同步 |
| `change` | `boolean` | 状态变化 |

> thumb 位移用 `left`（百分比相对父元素）而非 translateX；垂直居中用 `top:50%` + 负 margin。

---

## DewPopover 浮层

iOS 风格纯色浮层（无 glass、无描边、浅阴影），自研定位引擎 + 视口碰撞翻转。

### Props

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `modelValue` | `boolean` | `false` | 显隐（v-model） |
| `trigger` | `string` | `'click'` | `click` / `hover` |
| `placement` | `string` | `'bottom'` | `bottom` / `top`（自动翻转） |
| `showArrow` | `boolean` | `true` | 显示小三角箭头 |
| `width` | `string/number` | `''` | 浮层宽度 |
| `offset` | `number` | `8` | 与触发器的间距 |
| `disabled` | `boolean` | `false` | 禁用 |

### Slots

| 插槽 | 说明 |
|------|------|
| `trigger` | 触发器 |
| default | 浮层内容 |

> Teleport to body + 点击外部关闭 + 滚动/resize 更新位置 + hover 延迟关闭。

---

## DewDropdown 下拉菜单

基于 DewPopover 构建的菜单列表，danger 项红色高亮，点击自动关闭。

### Props

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `modelValue` | `boolean` | `false` | 显隐（v-model） |
| `trigger` | `string` | `'click'` | 触发方式 |
| `placement` | `string` | `'bottom'` | 定位 |
| `items` | `array` | `[]` | `[{ label, icon?, command, danger?, disabled? }]` |
| `disabled` | `boolean` | `false` | 禁用 |

### Events

| 事件 | 参数 | 说明 |
|------|------|------|
| `update:modelValue` | `boolean` | v-model 同步 |
| `select` | `command` | 选中某项 |

---

## DewIslandGroup 岛组

灵动岛生态容器：1 个主岛（可展开）+ N 个卫星岛（彩色胶囊，可展开），主岛与卫星岛互斥（同时只开一个）。

### Props

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `items` | `array` | `[]` | 卫星岛 `[{ value, unit?, color?(hex), ... }]`，其余字段透传给 #detail |
| `mainPanelWidth` | `string/number` | `300` | 主岛展开面板宽 |
| `satPanelWidth` | `string/number` | `240` | 卫星岛展开面板宽 |

### Slots

| 插槽 | 说明 |
|------|------|
| `main-trigger` | 主岛触发器（通常一个 DewButton 胶囊） |
| `main-content` | 主岛展开内容 |
| `detail` | 作用域 `{ item, index }`，每个卫星岛展开内容 |

> 卫星岛触发器：极简彩色胶囊（仅 value+unit，如 `18d`/`47h`/`#12`），pill 圆角，高 50px 与主岛等高，**无 backdrop-filter**（省性能），底色 = color 渐变淡彩。

---

## DewPostCard 帖子卡

社区帖子卡，双模式：full（社区页，完整可交互）/ compact（首页 feed 预览）。半透明实心卡（无 glass，适合列表多张）。

### Props

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `post` | `object` | — | `{ id, author, authorAvatar, publishTime, title?, content, images?, likes, views, comments, liked, bookmarked, badge? }` |
| `mode` | `string` | `'full'` | `full` / `compact` |

### Events

| 事件 | 参数 | 说明 |
|------|------|------|
| `click` | `post` | 点击整卡 |
| `user-click` | `id` | 点击头像/昵称 |
| `like` / `comment` / `bookmark` / `more` | `id` | 操作按钮 |
| `image-click` | `{ id, index, images }` | 点击图片 |

> full：正文 + 1~4 图网格 + 点赞/评论/收藏（点赞用爱心 SVG，已赞玫红、已收藏琥珀）。compact：左(发帖人+正文) / 右(缩略图) + 底部 点赞·观看·评论 / 更多(⋮)。`#话题` `@提及` 自动着色。

---

## 设计 Token

所有组件共享 `src/components/ui/tokens.css` 中定义的设计变量，通过 CSS 自定义属性实现完全组件化：

### 基础 Token

| 类别 | 变量示例 | 用途 |
|------|---------|------|
| 字体 | `--dew-font` | 统一字体栈（苹方/微软雅黑回退） |
| 品牌色 | `--color-primary` `--color-primary-light` | 主色调及浅底 |
| 语义色 | `--color-success` `--color-danger` `--color-warning` | 状态颜色 |
| 圆角 | `--radius-sm` `--radius-md` `--radius-lg` `--radius-full` | 8px / 12px / 16px / 全圆 |
| 阴影 | `--shadow-sm` `--shadow-md` `--shadow-lg` | 柔和多层阴影 |
| 毛玻璃 | `--glass-bg` `--glass-blur` `--glass-border` | 半透明 + 模糊参数 |

### 组件级 Token（`--dew-` 前缀）

| 类别 | 变量组 | 覆盖范围 |
|------|--------|---------|
| 文字 | `--dew-text` / `--dew-text-heading` / `--dew-text-muted` / `--dew-text-faint` | 4 级文字色 |
| 动画曲线 | `--dew-bounce` | 水滴弹性曲线，所有组件共享 |
| 按钮 glass | `--dew-btn-bg` / `--dew-btn-border` / `--dew-btn-shadow` | glass 默认态 + hover |
| 按钮 danger | `--dew-btn-danger-*` | danger 全态（bg/border/color/shadow/text-shadow） |
| 按钮 lit | `--dew-btn-lit-*` | 白光点亮全态 |
| 按钮 danger lit | `--dew-btn-danger-lit-*` | 红色光焰全态 |
| 按钮 ghost | `--dew-ghost-hover-*` | 幽灵按钮 hover |
| 光效层 | `--dew-glow-*` | indicator/highlight/ripple/text-active |
| 按钮栏 | `--dew-bar-*` | 容器 + 文字 + badge |
| 卡片 | `--dew-card-*` | 4 种变体（default/elevated/inset/glass）全态 |
| 卡片底色 | `--dew-tint-*-from` / `--dew-tint-*-to` | 6 种 accent 色彩渐变 |
| 浮岛 | `--dew-island-bg` / `--dew-island-border` / `--dew-island-radius` / `--dew-island-shadow` | 液态玻璃浮层，亮/暗自动覆盖 |

### 暗色模式

所有 `--dew-*` 变量在 `.theme-dark` 下自动覆盖为暗色值。切换主题只需在父元素上挂载 `theme-dark` / `theme-light` class：

```vue
<div :class="isDark ? 'theme-dark' : 'theme-light'">
  <DewButton>按钮</DewButton>
  <DewCard>卡片</DewCard>
</div>
```

自定义主题只需修改 `tokens.css` 中的变量值即可全局生效。

---

## 组件展示页面

开发环境中访问 `/ui-showcase` 可查看所有组件的实时效果和交互演示，含亮/暗模式切换。
