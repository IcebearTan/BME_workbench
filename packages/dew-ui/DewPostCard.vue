<template>
  <div :class="['dew-post', `dew-post--${mode}`]" @click="onCardClick">
    <!-- ━━ full 模式：完整正文 + 图片网格 + 操作行 ━━ -->
    <template v-if="mode === 'full'">
      <div class="dew-post__head">
        <DewImage shape="circle" :size="40" :src="post.authorAvatar" :initial="post.author || '?'" class="dew-post__avatar" @click.stop="onUserClick" />
        <div class="dew-post__user">
          <div class="dew-post__name-row">
            <span class="dew-post__name" @click.stop="onUserClick">{{ post.author }}</span>
            <span v-if="post.badge" class="dew-post__badge">{{ post.badge }}</span>
          </div>
          <span class="dew-post__time">{{ post.publishTime }}</span>
        </div>
      </div>

      <div class="dew-post__body">
        <div v-if="post.title" class="dew-post__title">{{ post.title }}</div>
        <p class="dew-post__text" v-html="formatContent(post.content)"></p>
        <div
          v-if="post.images && post.images.length"
          :class="['dew-post__images', `images-${Math.min(post.images.length, 4)}`]"
        >
          <DewImage
            v-for="(img, i) in post.images.slice(0, 4)"
            :key="i"
            :src="img"
            class="dew-post__image"
            @click.stop="onImageClick(i)"
          />
        </div>
      </div>

      <div class="dew-post__foot" @click.stop>
        <button class="dew-action" :class="{ 'is-liked': post.liked }" @click="onLike">
          <svg class="dew-action__icon dew-heart" viewBox="0 0 24 24" :fill="post.liked ? 'currentColor' : 'none'" stroke="currentColor" :stroke-width="post.liked ? 0 : 2">
            <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" />
          </svg>
          <span>{{ post.likes || 0 }}</span>
        </button>
        <button class="dew-action" @click="onComment">
          <el-icon class="dew-action__icon"><ChatDotRound /></el-icon>
          <span>{{ post.comments || 0 }}</span>
        </button>
        <button class="dew-action dew-action--bookmark" :class="{ 'is-bookmarked': post.bookmarked }" @click="onBookmark">
          <el-icon class="dew-action__icon"><component :is="post.bookmarked ? CollectionTag : Collection" /></el-icon>
        </button>
      </div>
    </template>

    <!-- ━━ compact 模式：左(发帖人+正文) / 右(图) + 底部统计/更多 ━━ -->
    <template v-else>
      <div class="dew-post__top">
        <!-- 左：发帖人信息 + 正文，塞进一个容器 -->
        <div class="dew-post__main">
          <div class="dew-post__head">
            <DewImage shape="circle" :size="36" :src="post.authorAvatar" :initial="post.author || '?'" class="dew-post__avatar" @click.stop="onUserClick" />
            <div class="dew-post__user">
              <div class="dew-post__name-row">
                <span class="dew-post__name" @click.stop="onUserClick">{{ post.author }}</span>
                <span v-if="post.badge" class="dew-post__badge">{{ post.badge }}</span>
              </div>
              <span class="dew-post__time">{{ post.publishTime }}</span>
            </div>
          </div>
          <div v-if="post.title" class="dew-post__title is-clamp-1">{{ post.title }}</div>
          <p class="dew-post__text is-clamp-2" v-html="formatContent(post.content)"></p>
        </div>
        <!-- 右：图片（贴着整块左侧，更高更大） -->
        <div v-if="post.images && post.images.length" class="dew-post__media" @click.stop="onImageClick(0)">
          <DewImage :src="post.images[0]" alt="" class="dew-post__media-img" />
        </div>
      </div>

      <div class="dew-post__foot dew-post__foot--split" @click.stop>
        <div class="dew-post__stats">
          <span class="dew-post__stat">
            <svg class="dew-post__stat-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" /></svg>
            {{ post.likes || 0 }}
          </span>
          <span class="dew-post__stat">
            <el-icon class="dew-post__stat-icon"><View /></el-icon>
            {{ post.views || 0 }}
          </span>
          <span class="dew-post__stat">
            <el-icon class="dew-post__stat-icon"><ChatDotRound /></el-icon>
            {{ post.comments || 0 }}
          </span>
        </div>
        <button class="dew-post__more" @click="onMore" aria-label="更多操作">
          <el-icon><MoreFilled /></el-icon>
        </button>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ChatDotRound, Collection, CollectionTag, View, MoreFilled } from '@element-plus/icons-vue'
import DewImage from './DewImage.vue'

const props = defineProps({
  /** 帖子：{ id, author, authorAvatar, publishTime, title?, content, images?, likes, views, comments, liked, bookmarked, badge? } */
  post: { type: Object, required: true },
  /** full（完整可交互）| compact（预览：左信息+正文 / 右图 + 底部统计/更多） */
  mode: { type: String, default: 'full' },
})

const emit = defineEmits(['click', 'user-click', 'like', 'comment', 'bookmark', 'more', 'image-click'])

// #话题 / @提及 着色
function formatContent(content) {
  if (!content) return ''
  return content
    .replace(/#(\S+)/g, '<span class="dew-tag">#$1</span>')
    .replace(/@(\S+)/g, '<span class="dew-mention">@$1</span>')
}

const onCardClick = () => emit('click', props.post)
const onUserClick = () => emit('user-click', props.post.authorId || props.post.id)
const onLike = () => emit('like', props.post.id)
const onComment = () => emit('comment', props.post.id)
const onBookmark = () => emit('bookmark', props.post.id)
const onMore = () => emit('more', props.post.id)
const onImageClick = (i) => emit('image-click', { id: props.post.id, index: i, images: props.post.images })
</script>

<style scoped>
/* ── 卡片表面：复用 --dew-card-* 默认 token（半透明实心，无 glass） ── */
.dew-post {
  background: var(--dew-card-bg);
  border: 1px solid var(--dew-card-border);
  border-radius: 16px;
  padding: 16px;
  box-shadow: var(--dew-card-shadow);
  color: var(--dew-text);
  font-family: var(--dew-font, inherit);
  cursor: pointer;
  transition: transform 0.28s var(--dew-bounce), box-shadow 0.28s var(--dew-bounce), background 0.28s ease;
}
.dew-post:hover {
  background: var(--dew-card-bg-hover);
  box-shadow: var(--dew-card-shadow-hover);
  transform: translateY(-2px);
}
.dew-post--compact {
  padding: 13px 15px;
  border-radius: 14px;
}

/* 头部 */
.dew-post__head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.dew-post__avatar { flex-shrink: 0; cursor: pointer; }
.dew-post__user { flex: 1; min-width: 0; }
.dew-post__name-row {
  display: flex;
  align-items: center;
  gap: 6px;
}
.dew-post__name {
  font-size: 14px;
  font-weight: 600;
  color: var(--dew-text-heading);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.dew-post__badge {
  flex-shrink: 0;
  font-size: 10px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 999px;
  color: #fff;
  background: linear-gradient(135deg, #3b82f6, #06b6d4);
}
.dew-post__time {
  font-size: 12px;
  color: var(--dew-text-faint);
}

/* 正文 */
.dew-post__title {
  font-size: 15px;
  font-weight: 700;
  color: var(--dew-text-heading);
  line-height: 1.4;
  margin-bottom: 5px;
}
.is-clamp-1 {
  display: -webkit-box;
  -webkit-line-clamp: 1;
  line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.dew-post__text {
  font-size: 14px;
  line-height: 1.6;
  color: var(--dew-text);
  margin: 0;
  word-break: break-word;
}
.is-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.dew-post__text :deep(.dew-tag),
.dew-post__text :deep(.dew-mention) {
  color: #3b82f6;
  cursor: pointer;
}
.dew-post__text :deep(.dew-tag):hover,
.dew-post__text :deep(.dew-mention):hover {
  text-decoration: underline;
}

/* full 图片网格：比例盒先占位（DewImage 三态接管，图未到不塌格） */
.dew-post__images {
  display: grid;
  gap: 4px;
  margin-top: 10px;
  border-radius: 10px;
  overflow: hidden;
}
.images-1 { grid-template-columns: 1fr; }
.images-2 { grid-template-columns: repeat(2, 1fr); }
.images-3 { grid-template-columns: repeat(2, 1fr); grid-template-rows: repeat(2, 128px); }
.images-3 .dew-post__image:first-child { grid-row: 1 / 3; }
.images-4 { grid-template-columns: repeat(2, 1fr); grid-template-rows: repeat(2, 128px); }
.dew-post__image {
  width: 100%;
  height: 100%;
  cursor: zoom-in;
  transition: opacity 0.2s;
}
.images-1 .dew-post__image { aspect-ratio: 16 / 10; max-height: 320px; }
.images-2 .dew-post__image { aspect-ratio: 1 / 1; }
.dew-post__image:hover { opacity: 0.92; }

/* ── full 操作行 ── */
.dew-post__foot {
  display: flex;
  align-items: center;
  gap: 22px;
  padding-top: 4px;
}
.dew-action {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: none;
  border: none;
  padding: 4px 2px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  color: var(--dew-text-muted);
  font-family: inherit;
  font-variant-numeric: tabular-nums;
  transition: color 0.2s ease;
}
.dew-action:hover { color: var(--dew-text-heading); }
.dew-action__icon { font-size: 17px; }
.dew-heart { width: 17px; height: 17px; }
.dew-action.is-liked { color: #f43f5e; }
.dew-action.is-bookmarked { color: #f59e0b; }
.dew-action--bookmark { margin-left: auto; }

/* ── compact：左 main(发帖人+正文) / 右 media(图) ── */
.dew-post__top {
  display: flex;
  gap: 14px;
  align-items: stretch;
}
.dew-post__main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.dew-post__media {
  flex-shrink: 0;
  width: 160px;
  min-height: 104px;
  border-radius: 12px;
  overflow: hidden;
  background: rgba(127, 127, 127, 0.1);
  cursor: zoom-in;
}
.dew-post__media-img {
  width: 100%;
  height: 100%;
  border-radius: 0;
  transition: opacity 0.2s;
}
.dew-post__media:hover .dew-post__media-img { opacity: 0.92; }

/* compact 底部：左统计 / 右更多 */
.dew-post__foot--split {
  justify-content: space-between;
  margin-top: 10px;
}
.dew-post__stats {
  display: flex;
  align-items: center;
  gap: 18px;
}
.dew-post__stat {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: var(--dew-text-faint);
  font-variant-numeric: tabular-nums;
}
.dew-post__stat-icon { font-size: 14px; }
.dew-post__stat .dew-post__stat-icon { width: 14px; height: 14px; }
.dew-post__more {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border: none;
  background: none;
  border-radius: 8px;
  cursor: pointer;
  color: var(--dew-text-faint);
  font-size: 16px;
  transition: background 0.2s ease, color 0.2s ease;
}
.dew-post__more:hover {
  background: var(--dew-popover-item-hover);
  color: var(--dew-text-heading);
}

@media (max-width: 768px) {
  .dew-post { padding: 14px; }
  .dew-post__foot { gap: 18px; }
  .dew-post__media { width: 130px; min-height: 90px; }
}
</style>
