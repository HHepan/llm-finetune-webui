<template>
  <div class="landing">
    <div class="landing-spinner"></div>
    <p class="landing-text">加载中...</p>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

// 在 setup 中就触发跳转，尽可能早
router.replace('/data')
</script>

<style scoped>
.landing {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
  height: 100dvh;
  background: #f4f6fa;
  gap: 16px;
}

.landing-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #e9edf2;
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin 0.65s linear infinite;
  box-sizing: border-box;
}

.landing-text {
  margin: 0;
  font-size: 14px;
  color: #94a3b8;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'PingFang SC', 'Helvetica Neue', sans-serif;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>