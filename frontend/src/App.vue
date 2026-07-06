<script setup lang="ts">
import { RouterView, RouterLink } from 'vue-router'
</script>

<template>
  <header class="topbar">
    <RouterLink to="/" class="brand">📄 Dokumente-OCR</RouterLink>
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
main {
  padding: 0;
}
</style>
