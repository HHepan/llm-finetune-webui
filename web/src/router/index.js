import { createRouter, createWebHistory } from 'vue-router'

const routes =[
  {
    path: '/',
    redirect: '/data' // 默认跳转到数据管理
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
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router