<template>
  <!-- 移动端路由：直接渲染，不要侧边栏 -->
  <template v-if="isMobileRoute">
    <router-view />
  </template>

  <!-- 桌面端路由：保持原有布局 -->
  <el-container v-else class="layout-container">
    <!-- 左侧侧边栏 -->
    <el-aside width="200px" class="aside">
      <div class="logo">
        <h3>LLM WebUI</h3>
      </div>
      <el-menu
        :default-active="$route.path"
        router
        class="el-menu-vertical"
        background-color="#2c3e50"
        text-color="#fff"
        active-text-color="#409eff"
      >
        <el-menu-item index="/data">
          <el-icon><Document /></el-icon>
          <span>数据管理</span>
        </el-menu-item>
        <el-menu-item index="/train">
          <el-icon><Cpu /></el-icon>
          <span>微调训练</span>
        </el-menu-item>
        <el-menu-item index="/chat">
          <el-icon><ChatDotRound /></el-icon>
          <span>对话测试</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <span class="header-title">{{ $route.meta.title }}</span>
        <div style="margin-left: auto;">
          <a href="/m/data" style="color: #409eff; text-decoration: none; font-size: 13px;">📱 手机版</a>
        </div>
      </el-header>

      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Document, Cpu, ChatDotRound } from '@element-plus/icons-vue'

const route = useRoute()
const isMobileRoute = computed(() => route.path.startsWith('/m'))
</script>

<style>
/* 全局样式重置 */
body, html {
  margin: 0;
  padding: 0;
  height: 100%;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
}

#app {
  height: 100vh;
}

.layout-container {
  height: 100%;
}

.aside {
  background-color: #2c3e50;
  display: flex;
  flex-direction: column;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  border-bottom: 1px solid #1a252f;
}

.el-menu-vertical {
  border-right: none;
}

.header {
  background-color: #fff;
  border-bottom: 1px solid #e6e6e6;
  display: flex;
  align-items: center;
  font-size: 18px;
  font-weight: bold;
  color: #333;
}

.main-content {
  background-color: #f0f2f5;
  padding: 20px;
}

.page-container {
  background: #fff;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  min-height: calc(100vh - 140px);
}
</style>