<script setup>
// 成员看板（工作台 III 追加）：全社成员名录——分组浏览 + 姓名/职位检索。
// 目的：让进入工作台的人日常混熟脸，派活/邀请/转交时不必再去问人或翻组织页。
// 数据源与组织架构页同接口（GET /organization 一次回全树），纯前端聚合，后端零改动；
// 点击成员进个人主页，点组名深链组织页（?group=）。
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { DewCard, DewTag, DewSkeleton, DewButton } from '@bme/dew-ui'
import DewImage from '@bme/dew-ui/DewImage.vue'
import { Search } from '@element-plus/icons-vue'
import api from '../api'
import { assetUrl } from '../utils/assets'
import { useWorkAccess } from '../composables/useWorkAccess'

const router = useRouter()
const { me } = useWorkAccess()

// ── 数据（与组织页同源；三段式） ──
const org = ref(null)
const loading = ref(true)
const loadFailed = ref(false)

async function load() {
  loading.value = true
  loadFailed.value = false
  try {
    const res = await api.get('/organization')
    org.value = res.data?.data || null
  } catch {
    org.value = null
    loadFailed.value = true
  } finally {
    loading.value = false
  }
}
onMounted(load)

// ── 平铺：管理层 + 各组（带父路径，子组重名可辨） ──
const officers = computed(() => {
  const list = []
  if (org.value?.president) list.push(org.value.president)
  list.push(...(org.value?.management || []))
  return list
})
const sectionsRaw = computed(() => {
  const out = []
  const walk = (nodes, parents) => {
    for (const n of nodes || []) {
      out.push({ id: n.id, name: n.name, parents, members: n.members || [] })
      walk(n.children, [...parents, n.name])
    }
  }
  walk(org.value?.tree, [])
  return out
})
// 我的工作区分组置顶（稳定排序），便于先认自己组的人
const myGroupIds = computed(() =>
  new Set((me.value?.workspaces || []).map(w => w.club_group_id)))
const sections = computed(() => {
  const mine = []
  const rest = []
  for (const s of sectionsRaw.value) (myGroupIds.value.has(s.id) ? mine : rest).push(s)
  return [...mine, ...rest]
})

// ── 检索（客户端即时过滤：姓名/职位/组名；组筛选） ──
const keyword = ref('')
const groupFilter = ref(null)

function sectionMatchesKw(s, q) {
  return s.name.toLowerCase().includes(q)
    || s.parents.some(p => p.toLowerCase().includes(q))
}
function memberMatchesKw(m, q) {
  return (m.username || '').toLowerCase().includes(q)
    || (m.title || '').toLowerCase().includes(q)
}
const visibleOfficers = computed(() => {
  const q = keyword.value.trim().toLowerCase()
  if (!q) return officers.value
  return officers.value.filter(o =>
    (o.username || '').toLowerCase().includes(q) || (o.title || '').toLowerCase().includes(q))
})
const visibleSections = computed(() => {
  let list = sections.value
  if (groupFilter.value) list = list.filter(s => s.id === groupFilter.value)
  const q = keyword.value.trim().toLowerCase()
  if (q) {
    list = list
      .map(s => sectionMatchesKw(s, q) ? s : { ...s, members: s.members.filter(m => memberMatchesKw(m, q)) })
      .filter(s => s.members.length || sectionMatchesKw(s, q))
  }
  return list
})
const hasAnyContent = computed(() =>
  officers.value.length || sectionsRaw.value.some(s => s.members.length))
const totalPeople = computed(() => {
  const ids = new Set()
  for (const o of officers.value) ids.add(o.id)
  for (const s of sectionsRaw.value) for (const m of s.members) ids.add(m.id)
  return ids.size
})

function goProfile(id) {
  if (id) window.location.assign((import.meta.env.VITE_TRAINING_URL || '') + '/profile/' + id)
}
function goOrg(id) {
  groupFilter.value = id
}
</script>

<template>
  <div class="members-view">
    <!-- 工具栏：检索 + 组筛选 + 总数 -->
    <div class="filter-bar">
      <el-input v-model="keyword" :prefix-icon="Search" style="width: 220px;"
                placeholder="搜索姓名 / 职位 / 组名" clearable />
      <el-select v-model="groupFilter" style="width: 180px;" placeholder="全部组别" clearable>
        <el-option v-for="s in sections" :key="s.id"
                   :label="s.parents.length ? s.parents.join(' / ') + ' / ' + s.name : s.name"
                   :value="s.id" />
      </el-select>
      <span class="total-hint ws-num">共 {{ totalPeople }} 名成员</span>
    </div>

    <!-- 骨架 -->
    <template v-if="loading">
      <DewCard v-for="i in 3" :key="i" size="md" variant="flat" class="sk-card">
        <DewSkeleton variant="text" :lines="2" />
      </DewCard>
    </template>

    <!-- 失败态 -->
    <DewCard v-else-if="loadFailed" size="md" variant="flat">
      <p class="state-text">成员名录加载失败，请重试</p>
      <DewButton size="sm" :loading="loading" @click="load">重试</DewButton>
    </DewCard>

    <!-- 空库 -->
    <DewCard v-else-if="!hasAnyContent" size="md" variant="flat">
      <p class="state-text">组织架构待发布：干事任命与成员归属录入后会在这里展示</p>
    </DewCard>

    <template v-else>
      <!-- 管理层（社长 + 管理层） -->
      <template v-if="visibleOfficers.length">
        <div class="sec-head">
          <span class="sec-title">社长与管理层</span>
          <span class="sec-count ws-num">{{ visibleOfficers.length }} 人</span>
        </div>
        <DewCard size="md" variant="flat" class="sec-card">
          <div class="member-grid">
            <div v-for="o in visibleOfficers" :key="o.id" class="member-chip"
                 @click="goProfile(o.id)">
              <DewImage shape="circle" :size="56" :src="assetUrl(o.avatar) || null"
                        :initial="o.username || '?'" class="member-avatar member-avatar--officer" />
              <span class="member-name">{{ o.username }}</span>
              <span class="member-tags">
                <DewTag type="warning" size="sm" round>{{ o.title }}</DewTag>
              </span>
            </div>
          </div>
        </DewCard>
      </template>

      <!-- 各组（我的工作区置顶） -->
      <template v-for="s in visibleSections" :key="s.id">
        <div class="sec-head">
          <button type="button" class="sec-title sec-title--link"
                  :title="'在组织架构中查看 ' + s.name" @click="goOrg(s.id)">
            <span v-if="s.parents.length" class="sec-path">{{ s.parents.join(' / ') }} / </span>{{ s.name }}
          </button>
          <DewTag v-if="myGroupIds.has(s.id)" type="primary" size="sm" round>我的工作区</DewTag>
          <span class="sec-count ws-num">{{ s.members.length }} 人</span>
        </div>
        <DewCard size="md" variant="flat" class="sec-card">
          <div class="member-grid">
            <div v-for="m in s.members" :key="m.id" class="member-chip" @click="goProfile(m.id)">
              <DewImage shape="circle" :size="48" :src="assetUrl(m.avatar) || null"
                        :initial="m.username || '?'" class="member-avatar" />
              <span class="member-name">{{ m.username }}</span>
              <span class="member-tags">
                <DewTag v-if="m.is_leader" type="primary" size="sm" round>组长</DewTag>
                <DewTag v-else-if="m.title" type="neutral" size="sm" round>{{ m.title }}</DewTag>
                <DewTag v-if="m.slot === 'secondary'" type="neutral" size="sm" round>辅</DewTag>
              </span>
            </div>
          </div>
          <p v-if="!s.members.length" class="sec-empty">本组暂无直挂成员 · 招新中</p>
        </DewCard>
      </template>

      <!-- 检索无结果 -->
      <DewCard v-if="!visibleOfficers.length && !visibleSections.length" size="md" variant="flat">
        <p class="state-text">没有匹配「{{ keyword.trim() }}」的成员</p>
      </DewCard>
    </template>
  </div>
</template>

<style scoped>
.filter-bar {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  margin-bottom: 16px;
}
.total-hint { font-size: 12.5px; color: var(--dew-text-muted); }

.sk-card { margin-bottom: 12px; }
.state-text { margin: 0 0 12px; font-size: 13px; color: var(--dew-text-muted); }

/* ── 分区头：组名（可深链组织页）+ 我的标记 + 人数 ── */
.sec-head {
  display: flex; align-items: center; gap: 8px;
  margin: 18px 0 10px;
}
.sec-head:first-of-type { margin-top: 0; }
.sec-title {
  font-size: 14px; font-weight: 600; color: var(--dew-text-heading);
  border: none; background: transparent; padding: 0; font-family: inherit;
}
.sec-title--link { cursor: pointer; }
.sec-title--link:hover { color: var(--color-primary); }
.sec-path { font-size: 12px; font-weight: 400; color: var(--dew-text-faint); }
.sec-count { margin-left: auto; font-size: 12px; color: var(--dew-text-muted); }
.sec-card { margin-bottom: 4px; }
.sec-empty { margin: 0; padding: 4px 0; font-size: 12.5px; color: var(--dew-text-muted); }

/* ── 成员块：头像居中 + 姓名 + 身份标签（首字随头像放大，保证默认头像大气） ── */
.member-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(148px, 1fr)); gap: 10px;
}
.member-chip {
  display: flex; flex-direction: column; align-items: center; gap: 7px;
  padding: 14px 8px 10px; border-radius: 10px; cursor: pointer;
  transition: background 0.2s ease;
}
.member-chip:hover { background: var(--ws-hover); }
/* 首字大小由 DewImage 按直径锚定（size prop），无需外设字号 */
.member-avatar--officer { box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-primary) 14%, transparent); }
.member-name {
  font-size: 13.5px; font-weight: 600; color: var(--dew-text-heading);
  max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.member-tags { display: flex; gap: 4px; flex-wrap: wrap; justify-content: center; min-height: 18px; }

@media (max-width: 768px) {
  .filter-bar :deep(.el-input), .filter-bar :deep(.el-select) { width: 140px !important; }
  .member-grid { grid-template-columns: repeat(auto-fill, minmax(116px, 1fr)); }
}
</style>
