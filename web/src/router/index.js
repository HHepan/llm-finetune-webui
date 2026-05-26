import { createRouter, createWebHistory } from 'vue-router'

const routes =[
  // === 桌面端路由 ===
  {
    path: '/',
    redirect: '/data'
  },
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

export default router