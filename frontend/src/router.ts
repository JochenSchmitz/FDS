import { createRouter, createWebHistory } from 'vue-router'
import DocumentsView from './views/DocumentsView.vue'
import ViewerView from './views/ViewerView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'documents', component: DocumentsView },
    { path: '/doc/:id', name: 'viewer', component: ViewerView, props: true },
  ],
})
