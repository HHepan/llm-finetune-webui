import { createRouter, createWebHistory } from 'vue-router'

const routes =[
  // === 着陆页（入口检测）===
  {
    path: '/',
    name: 'Landing',
    component: () => import('../views/LandingPage.vue')
  },

  // === 桌面端路由 ===
  {
    path: '/data',
    name: 'DataManage',
    component: () => import('../views/DataManage.vue'),
    meta: { title: '数据管理' }
  },
  {
    path: '/train',
    name: 'Train',
    component: () => import('../views/Train.vue'),
    meta: { title: '微调训练' }
  },
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('../views/Chat.vue'),
    meta: { title: '对话测试' }
  },

  // === 移动端路由 ===
  {
    path: '/m',
    component: () => import('../mobile/MobileLayout.vue'),
    children: [
      { path: '', redirect: '/m/data' },
      {
        path: 'data',
        name: 'MData',
        component: () => import('../mobile/views/MData.vue'),
        meta: { title: '数据管理' }
      },
      {
        path: 'train',
        name: 'MTrain',
        component: () => import('../mobile/views/MTrain.vue'),
        meta: { title: '微调训练' }
      },
      {
        path: 'chat',
        name: 'MChat',
        component: () => import('../mobile/views/MChat.vue'),
        meta: { title: '对话测试' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 移动端自动跳转守卫（在组件渲染之前执行，避免闪烁）
const isMobileDevice = () => {
  return /Android|iPhone|iPad|iPod|webOS|BlackBerry|IEMobile|Opera Mini|Mobi/i.test(navigator.userAgent)
    || window.innerWidth < 768
}

router.beforeEach((to, from, next) => {
  const isMobile = isMobileDevice()
  const forcedDesktop = localStorage.getItem('__forceDesktop')
  // 移动端访问非 /m 路由 → 自动跳转
  if (isMobile && !forcedDesktop && !to.path.startsWith('/m')) {
    const targetPath = to.path === '/' ? '/m/data' : '/m' + to.path
    return next(targetPath)
  }
  next()
})

export default router