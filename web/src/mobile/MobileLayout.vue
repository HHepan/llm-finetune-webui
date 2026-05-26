<template>
  <div class="m-root">
    <!-- 顶部状态栏+标题栏 -->
    <div class="m-header">
      <div class="m-header-left">
        <span class="m-header-title">{{ $route.meta?.title || 'LLM WebUI' }}</span>
      </div>
      <div class="m-header-right">
        <a href="/data" class="m-desktop-link">桌面版</a>
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
        <span class="m-tabbar-icon">{{ tab.icon }}</span>
        <span class="m-tabbar-label">{{ tab.label }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const tabs = [
  { path: '/m/data', icon: '📋', label: '数据' },
  { path: '/m/train', icon: '⚙️', label: '训练' },
  { path: '/m/chat', icon: '💬', label: '对话' }
]

const goTab = (path) => {
  if (route.path !== path) {
    router.push(path)
  }
}
</script>

<style>
/* ========== 全局重置 ========== */
html, body {
  margin: 0;
  padding: 0;
  height: 100%;
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Helvetica Neue', Arial, sans-serif;
  background: #f5f6f8;
  -webkit-text-size-adjust: 100%;
  -webkit-tap-highlight-color: transparent;
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
  background: #f5f6f8;
}

/* 顶部栏 */
.m-header {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 48px;
  padding: 0 16px;
  background: #2c3e50;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  z-index: 10;
  box-shadow: 0 1px 4px rgba(0,0,0,0.1);
}

.m-header-title {
  font-size: 16px;
}

.m-desktop-link {
  color: #95a5a6;
  text-decoration: none;
  font-size: 12px;
  font-weight: 400;
  padding: 4px 8px;
  border-radius: 4px;
  border: 1px solid #4a5e70;
}

.m-desktop-link:active {
  background: rgba(255,255,255,0.1);
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
  background: #fff;
  border-top: 1px solid #e8e8e8;
  padding-bottom: env(safe-area-inset-bottom, 0);
  z-index: 10;
}

.m-tabbar-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  padding: 6px 0;
  cursor: pointer;
  color: #999;
  transition: color 0.2s;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}

.m-tabbar-item.active {
  color: #409eff;
}

.m-tabbar-icon {
  font-size: 22px;
  line-height: 1;
}

.m-tabbar-label {
  font-size: 11px;
  line-height: 1;
}

/* ========== 移动端通用组件样式 ========== */

/* 卡片容器 */
.m-card {
  background: #fff;
  border-radius: 10px;
  padding: 14px;
  margin-bottom: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

/* 操作栏 - 顶部的选择器和按钮组 */
.m-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
  align-items: center;
}

.m-actions .el-select {
  flex: 1;
  min-width: 0;
}

.m-actions .el-button {
  flex-shrink: 0;
}

/* 卡片列表项 */
.m-list-item {
  background: #fff;
  border-radius: 10px;
  padding: 14px;
  margin-bottom: 10px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

.m-list-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 12px;
  color: #999;
}

.m-list-item-body {
  font-size: 14px;
  line-height: 1.5;
  color: #333;
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
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #f0f0f0;
}

/* 标签 */
.m-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.m-tag-info { background: #e6f7ff; color: #1890ff; }
.m-tag-warning { background: #fff7e6; color: #fa8c16; }
.m-tag-success { background: #f6ffed; color: #52c41a; }
.m-tag-danger { background: #fff1f0; color: #f5222d; }

/* 空状态 */
.m-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #bbb;
  font-size: 14px;
}

.m-empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

/* 全屏弹层 */
.m-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  z-index: 1000;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
}

.m-modal-content {
  background: #fff;
  border-radius: 16px 16px 0 0;
  max-height: 85vh;
  overflow-y: auto;
  padding: 20px 16px;
  padding-bottom: calc(16px + env(safe-area-inset-bottom, 0));
}

.m-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  font-size: 16px;
  font-weight: 600;
}

.m-modal-close {
  font-size: 24px;
  color: #999;
  cursor: pointer;
  padding: 4px;
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
}

.m-content .el-slider {
  flex: 1;
}

.m-content .el-card {
  border-radius: 10px;
}

.m-content .el-tabs__item {
  font-size: 13px;
  padding: 0 12px;
}

/* 分页简化 */
.m-pager {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  padding: 12px 0;
  font-size: 13px;
  color: #666;
}

.m-pager button {
  border: 1px solid #ddd;
  background: #fff;
  border-radius: 6px;
  padding: 6px 14px;
  font-size: 13px;
  color: #333;
  cursor: pointer;
}

.m-pager button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.m-pager button:active:not(:disabled) {
  background: #f0f0f0;
}

.m-pager span {
  min-width: 24px;
  text-align: center;
}

/* 滚动条优化 */
.m-content::-webkit-scrollbar {
  width: 0;
  height: 0;
}
</style>