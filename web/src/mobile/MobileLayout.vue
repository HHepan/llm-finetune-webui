<template>
  <div class="m-root">
    <!-- 顶部标题栏 -->
    <div class="m-header">
      <div class="m-header-left">
        <div class="m-header-brand">
          <span class="m-header-dot"></span>
          <span class="m-header-title">{{ $route.meta?.title || 'LLM WebUI' }}</span>
        </div>
      </div>
      <div class="m-header-accent"></div>
      <div class="m-header-right">
        <button class="m-theme-toggle" @click="toggleTheme" :title="isDark ? '切换亮色' : '切换暗色'">
          <span v-if="isDark">☀️</span>
          <span v-else>🌙</span>
        </button>
      </div>
    </div>

    <!-- 内容区 -->
    <div class="m-content">
      <router-view />
    </div>

    <!-- 底部Tab导航 -->
    <div class="m-tabbar">
      <div
        v-for="tab in tabs"
        :key="tab.path"
        class="m-tabbar-item"
        :class="{ active: $route.path === tab.path }"
        @click="goTab(tab.path)"
      >
        <span class="m-tabbar-icon" v-html="tab.icon"></span>
        <span class="m-tabbar-label">{{ tab.label }}</span>
        <span v-if="$route.path === tab.path" class="m-tabbar-dot"></span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter, useRoute } from 'vue-router'
import { ref, onMounted } from 'vue'

const isDark = ref(false)

const applyTheme = (dark) => {
  isDark.value = dark
  document.documentElement.dataset.theme = dark ? 'dark' : ''
  try { localStorage.setItem('m-theme', dark ? 'dark' : 'light') } catch {}
}

const toggleTheme = () => applyTheme(!isDark.value)

onMounted(() => {
  try {
    const saved = localStorage.getItem('m-theme')
    if (saved === 'dark') applyTheme(true)
  } catch {}
})

const router = useRouter()
const route = useRoute()

const tabs = [
  { path: '/m/data', icon: '&#9776;', label: '数据' },
  { path: '/m/train', icon: '&#9654;', label: '训练' },
  { path: '/m/chat', icon: '&#9679;', label: '对话' }
]

const goTab = (path) => {
  if (route.path !== path) {
    router.push(path)
  }
}
</script>

<style>
/* ========== CSS 变量 ========== */
:root {
  --c-primary: #6366f1;
  --c-primary-light: #818cf8;
  --c-primary-dark: #4f46e5;
  --c-primary-soft: #eef2ff;
  --c-primary-bg: rgba(99, 102, 241, 0.08);
  --c-success: #10b981;
  --c-success-soft: #ecfdf5;
  --c-warning: #f59e0b;
  --c-warning-soft: #fffbeb;
  --c-danger: #ef4444;
  --c-danger-soft: #fef2f2;
  --c-info: #6366f1;
  --c-bg: #f4f6fa;
  --c-surface: #ffffff;
  --c-text-primary: #0f172a;
  --c-text-secondary: #64748b;
  --c-text-muted: #94a3b8;
  --c-border: #e9edf2;
  --c-border-light: #f1f4f8;
  --shadow-sm: 0 1px 2px rgba(99, 102, 241, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04);
  --shadow-md: 0 4px 12px rgba(99, 102, 241, 0.08), 0 2px 4px rgba(0, 0, 0, 0.03);
  --shadow-lg: 0 8px 24px rgba(99, 102, 241, 0.10), 0 4px 8px rgba(0, 0, 0, 0.04);
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 20px;
  --c-tabbar-bg: rgba(255, 255, 255, 0.85);
  --c-overlay-bg: rgba(15, 23, 42, 0.4);
  --c-scrollbar-thumb: #ccc;
  --c-avatar-assistant-bg: #f0f0ff;
}

/* ========== 暗色主题 ========== */
[data-theme="dark"] {
  --c-bg: #0d1117;
  --c-surface: #161b22;
  --c-text-primary: #e6edf3;
  --c-text-secondary: #8b949e;
  --c-text-muted: #6e7681;
  --c-border: #30363d;
  --c-border-light: #21262d;
  --c-primary-soft: rgba(99, 102, 241, 0.2);
  --c-primary-bg: rgba(99, 102, 241, 0.12);
  --c-success-soft: rgba(16, 185, 129, 0.2);
  --c-warning-soft: rgba(245, 158, 11, 0.2);
  --c-danger-soft: rgba(255, 77, 77, 0.2);
  --c-tabbar-bg: rgba(22, 27, 34, 0.88);
  --c-overlay-bg: rgba(0, 0, 0, 0.6);
  --c-scrollbar-thumb: #404854;
  --c-avatar-assistant-bg: var(--c-primary-soft);
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.4), 0 1px 3px rgba(0, 0, 0, 0.5);
  --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.5), 0 2px 4px rgba(0, 0, 0, 0.4);
  --shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.6), 0 4px 8px rgba(0, 0, 0, 0.4);

  /* ===== Element Plus 组件暗色覆盖 ===== */
  --el-bg-color: #141414;
  --el-bg-color-overlay: #1d1e1f;
  --el-text-color-primary: #e5eaf3;
  --el-text-color-regular: #cfd3dc;
  --el-text-color-secondary: #a3a6ad;
  --el-text-color-placeholder: #8d9095;
  --el-border-color: #4c4d4f;
  --el-border-color-light: #363637;
  --el-border-color-lighter: #2b2b2c;
  --el-border-color-extra-light: #1d1d1d;
  --el-fill-color: #303030;
  --el-fill-color-light: #262727;
  --el-fill-color-lighter: #1d1d1d;
  --el-fill-color-extra-light: #191919;
  --el-fill-color-blank: #1d1e1f;
  --el-mask-color: rgba(0, 0, 0, 0.8);
  --el-color-white: #1d1e1f;

  /* 输入框 */
  --el-input-bg-color: #1d1e1f;
  --el-input-border-color: #4c4d4f;
  --el-input-hover-border-color: var(--c-primary-light);
  --el-input-focus-border-color: var(--c-primary);
  --el-input-text-color: #e5eaf3;
  --el-input-placeholder-color: #8d9095;
  --el-input-icon-color: #8d9095;

  /* 下拉选择器 */
  --el-select-dropdown-bg-color: #1d1e1f;
  --el-select-dropdown-border-color: #363637;
  --el-select-option-hover-bg-color: #262727;
  --el-select-option-selected-bg-color: rgba(99, 102, 241, 0.15);
  --el-select-option-selected-text-color: var(--c-primary-light);

  /* 数字输入框 */
  --el-input-number-controls-bg-color: #262727;

  /* 按钮 */
  --el-button-bg-color: #262727;
  --el-button-border-color: #4c4d4f;
  --el-button-hover-bg-color: #303030;
  --el-button-hover-border-color: #63636f;
  --el-button-text-color: #cfd3dc;

  /* 进度条 */
  --el-progress-border-radius: 4px;

  /* 滑块 */
  --el-slider-runway-bg-color: #30363d;
  --el-slider-button-bg-color: #1d1e1f;
  --el-slider-stop-bg-color: #4c4d4f;

  /* 卡片 */
  --el-card-bg-color: var(--c-surface);
  --el-card-border-color: var(--c-border-light);
}

/* ========== 全局重置 ========== */
html, body {
  margin: 0;
  padding: 0;
  height: 100%;
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'PingFang SC', 'Helvetica Neue', sans-serif;
  background: var(--c-bg);
  -webkit-text-size-adjust: 100%;
  -webkit-tap-highlight-color: transparent;
  color: var(--c-text-primary);
}

/* ========== 移动端布局 ========== */
.m-root {
  text-align: left;
  display: flex;
  flex-direction: column;
  height: 100vh;
  height: 100dvh;
  max-width: 100vw;
  overflow: hidden;
  background: var(--c-bg);
}

/* 顶部栏 */
.m-header {
  flex-shrink: 0;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 48px;
  padding: 0 16px;
  background: var(--c-surface);
  color: var(--c-text-primary);
  font-size: 16px;
  font-weight: 600;
  z-index: 10;
}

.m-header-accent {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--c-primary), var(--c-primary-light), #a78bfa);
  opacity: 0.6;
}

.m-header-brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.m-header-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--c-primary), #a78bfa);
  flex-shrink: 0;
}

.m-header-title {
  font-size: 16px;
  letter-spacing: 0.3px;
}

.m-header-right {
  display: flex;
  align-items: center;
  gap: 8px;
  z-index: 1;
}

.m-theme-toggle {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 50%;
  background: var(--c-primary-bg);
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
  padding: 0;
  transition: all 0.25s ease;
  color: var(--c-primary);
}

.m-theme-toggle:active {
  transform: scale(0.88);
  background: var(--c-primary-soft);
}

.m-desktop-link {
  color: var(--c-text-muted);
  text-decoration: none;
  font-size: 12px;
  font-weight: 500;
  padding: 5px 12px;
  border-radius: 20px;
  background: var(--c-primary-bg);
  color: var(--c-primary);
  transition: all 0.2s;
}

.m-desktop-link:active {
  background: rgba(99, 102, 241, 0.15);
  transform: scale(0.96);
}

/* 内容区 */
.m-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  -webkit-overflow-scrolling: touch;
  padding: 12px;
  padding-bottom: 8px;
}

/* 底部Tab栏 */
.m-tabbar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  height: 56px;
  background: var(--c-tabbar-bg);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-top: 1px solid var(--c-border);
  padding-bottom: env(safe-area-inset-bottom, 0);
  z-index: 10;
  position: relative;
}

.m-tabbar-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1px;
  padding: 6px 0 4px;
  cursor: pointer;
  color: var(--c-text-muted);
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  user-select: none;
  -webkit-tap-highlight-color: transparent;
  position: relative;
}

.m-tabbar-item:active {
  transform: scale(0.92);
}

.m-tabbar-item.active {
  color: var(--c-primary);
}

.m-tabbar-icon {
  font-size: 20px;
  line-height: 1;
  transition: transform 0.2s;
}

.m-tabbar-item.active .m-tabbar-icon {
  transform: translateY(-1px);
}

.m-tabbar-label {
  font-size: 10px;
  line-height: 1;
  font-weight: 500;
  letter-spacing: 0.2px;
}

.m-tabbar-dot {
  position: absolute;
  top: 2px;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--c-primary);
  animation: tabDotIn 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes tabDotIn {
  from { opacity: 0; transform: scale(0); }
  to { opacity: 1; transform: scale(1); }
}

/* ========== 移动端通用组件样式 ========== */

/* 卡片容器 */
.m-card {
  background: var(--c-surface);
  border-radius: var(--radius-md);
  padding: 16px;
  margin-bottom: 12px;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--c-border-light);
  transition: box-shadow 0.2s;
}

.m-card:active {
  box-shadow: var(--shadow-md);
}

/* 操作栏 */
.m-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 14px;
  align-items: center;
}

.m-actions .el-select {
  flex: 1;
  min-width: 0;
}

.m-actions .el-button {
  flex-shrink: 0;
}

/* Element Plus 选择器圆角统一 */
.m-content .el-select .el-input__wrapper {
  border-radius: var(--radius-sm);
  box-shadow: 0 0 0 1px var(--c-border) inset;
  transition: box-shadow 0.2s;
}

.m-content .el-select .el-input__wrapper.is-focus {
  box-shadow: 0 0 0 2px var(--c-primary) inset;
}

.m-content .el-select .el-input__inner {
  font-size: 13px;
}

/* 卡片列表项 */
.m-list-item {
  background: var(--c-surface);
  border-radius: var(--radius-md);
  padding: 16px;
  margin-bottom: 10px;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--c-border-light);
  transition: all 0.2s;
}

.m-list-item:active {
  box-shadow: var(--shadow-md);
  border-color: var(--c-primary-soft);
}

.m-list-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 12px;
  color: var(--c-text-muted);
}

.m-list-item-body {
  font-size: 14px;
  line-height: 1.6;
  color: var(--c-text-primary);
  word-break: break-word;
}

.m-list-item-body .conversation-preview {
  max-height: 4.5em;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
}

.m-list-item-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--c-border-light);
}

/* 标签 */
.m-tag {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  line-height: 1.4;
  letter-spacing: 0.2px;
}

.m-tag-info { background: var(--c-primary-soft); color: var(--c-primary); }
.m-tag-warning { background: var(--c-warning-soft); color: var(--c-warning); }
.m-tag-success { background: var(--c-success-soft); color: var(--c-success); }
.m-tag-danger { background: var(--c-danger-soft); color: var(--c-danger); }

/* 空状态 */
.m-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 20px;
  color: var(--c-text-muted);
  font-size: 14px;
}

.m-empty-icon {
  font-size: 44px;
  margin-bottom: 14px;
  opacity: 0.7;
}

/* 加载 Spinner */
.m-spinner {
  width: 28px;
  height: 28px;
  border: 3px solid var(--c-border);
  border-top-color: var(--c-primary);
  border-radius: 50%;
  animation: m-spin 0.65s linear infinite;
  box-sizing: border-box;
}

.m-spinner--lg {
  width: 40px;
  height: 40px;
  border-width: 3.5px;
}

.m-spinner--inline {
  display: inline-block;
  width: 14px;
  height: 14px;
  border-width: 2px;
  vertical-align: middle;
  margin-right: 4px;
}

@keyframes m-spin {
  to { transform: rotate(360deg); }
}

/* 空状态 SVG 图标 */
.m-empty-icon-svg {
  margin-bottom: 14px;
  opacity: 0.5;
}

/* 全屏弹层（底部弹出） */
.m-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--c-overlay-bg);
  z-index: 1000;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  animation: overlayIn 0.2s ease;
}

@keyframes overlayIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.m-modal-content {
  background: var(--c-surface);
  border-radius: var(--radius-xl) var(--radius-xl) 0 0;
  max-height: 85vh;
  overflow-y: auto;
  padding: 0 20px 20px;
  padding-bottom: calc(20px + env(safe-area-inset-bottom, 0));
  animation: slideUp 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes slideUp {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}

.m-modal-header {
position: sticky;
  top: 0;
  z-index: 1;
  background: var(--c-surface);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 0 16px;
  font-size: 16px;
  font-weight: 600;
  color: var(--c-text-primary);
}

.m-modal-close {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-size: 20px;
  color: var(--c-text-muted);
  cursor: pointer;
  transition: all 0.2s;
}

.m-modal-close:active {
  background: var(--c-border-light);
  color: var(--c-text-secondary);
}

/* 底部安全区适配 */
@supports (padding-bottom: env(safe-area-inset-bottom)) {
  .m-content {
    padding-bottom: calc(8px + env(safe-area-inset-bottom));
  }
}

/* Element Plus 移动端覆盖 */
.m-content .el-select,
.m-content .el-input,
.m-content .el-input-number {
  width: 100% !important;
}

.m-content .el-form-item {
  margin-bottom: 12px;
}

.m-content .el-form-item__label {
  font-size: 13px;
  padding-bottom: 4px;
  color: var(--c-text-secondary);
  font-weight: 500;
}

.m-content .el-slider {
  flex: 1;
}

.m-content .el-slider__bar {
  background: linear-gradient(90deg, var(--c-primary), var(--c-primary-light));
}

.m-content .el-slider__button {
  border-color: var(--c-primary);
}

.m-content .el-card {
  border-radius: var(--radius-md);
  border: 1px solid var(--c-border-light);
}

.m-content .el-tabs__item {
  font-size: 13px;
  padding: 0 12px;
  color: var(--c-text-muted);
}

.m-content .el-tabs__item.is-active {
  color: var(--c-primary);
}

.m-content .el-tabs__active-bar {
  background: var(--c-primary);
}

/* Element Plus 按钮美化 */
.m-content .el-button--primary {
  --el-button-bg-color: var(--c-primary);
  --el-button-border-color: var(--c-primary);
  --el-button-hover-bg-color: var(--c-primary-light);
  --el-button-hover-border-color: var(--c-primary-light);
  --el-button-active-bg-color: var(--c-primary-dark);
  --el-button-active-border-color: var(--c-primary-dark);
}

.m-content .el-button--success {
  --el-button-bg-color: var(--c-success);
  --el-button-border-color: var(--c-success);
}

.m-content .el-button--warning {
  --el-button-bg-color: var(--c-warning);
  --el-button-border-color: var(--c-warning);
}

.m-content .el-button--danger {
  --el-button-bg-color: var(--c-danger);
  --el-button-border-color: var(--c-danger);
}

.m-content .el-button.is-plain {
  --el-button-bg-color: transparent;
}

/* 分页简化 */
.m-pager {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  padding: 16px 0;
  font-size: 13px;
  color: var(--c-text-muted);
}

.m-pager button {
  border: 1px solid var(--c-border);
  background: var(--c-surface);
  border-radius: var(--radius-sm);
  padding: 6px 16px;
  font-size: 13px;
  font-weight: 500;
  color: var(--c-text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.m-pager button:active:not(:disabled) {
  background: var(--c-primary-soft);
  border-color: var(--c-primary-light);
  color: var(--c-primary);
}

.m-pager button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.m-pager span {
  min-width: 28px;
  text-align: center;
  font-weight: 600;
  color: var(--c-text-primary);
}

/* 滚动条优化 */
.m-content::-webkit-scrollbar {
  width: 0;
  height: 0;
}
</style>