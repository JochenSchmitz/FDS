<script setup lang="ts">
import { RouterView, RouterLink, useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore()
const router = useRouter()

async function logout() {
  await auth.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <header class="topbar">
    <RouterLink to="/" class="brand">📄 Dokumente-OCR</RouterLink>
    <span class="spacer" />
    <template v-if="auth.loggedIn">
      <span class="user">{{ auth.email }}</span>
      <button @click="logout">Abmelden</button>
    </template>
  </header>
  <main>
    <RouterView />
  </main>
</template>

<style scoped>
.topbar {
  display: flex;
  align-items: center;
  padding: 0.6rem 1.2rem;
  border-bottom: 1px solid var(--border);
}
.brand {
  font-weight: 700;
  color: var(--text-h);
  text-decoration: none;
  font-size: 1.05rem;
}
.spacer {
  flex: 1;
}
.user {
  color: var(--text-dim);
  font-size: 0.85rem;
  margin-right: 0.6rem;
}
main {
  padding: 0;
}
</style>
