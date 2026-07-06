import { createRouter, createWebHistory } from 'vue-router'
import DocumentsView from './views/DocumentsView.vue'
import LoginView from './views/LoginView.vue'
import ViewerView from './views/ViewerView.vue'
import { useAuthStore } from './stores/auth'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: LoginView },
    { path: '/', name: 'documents', component: DocumentsView },
    { path: '/doc/:id', name: 'viewer', component: ViewerView, props: true },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.check()
  if (to.name !== 'login' && !auth.loggedIn) {
    return { name: 'login', query: { weiter: to.fullPath } }
  }
  if (to.name === 'login' && auth.loggedIn) {
    return { name: 'documents' }
  }
})
