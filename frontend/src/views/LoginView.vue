<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const email = ref('')
const password = ref('')
const busy = ref(false)

async function submit() {
  busy.value = true
  try {
    if (await auth.login(email.value.trim(), password.value)) {
      const target = (route.query.weiter as string) || '/'
      router.push(target)
    }
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="login-wrap">
    <form class="login" @submit.prevent="submit">
      <h1>📄 FDS — FES Dokumentenservice</h1>
      <p class="hint">Bitte anmelden — die Sitzung gilt 7 Tage.</p>
      <label>
        E-Mail
        <input v-model="email" type="email" autocomplete="username" required />
      </label>
      <label>
        Passwort
        <input
          v-model="password"
          type="password"
          autocomplete="current-password"
          required
        />
      </label>
      <p v-if="auth.error" class="error">{{ auth.error }}</p>
      <button class="primary" type="submit" :disabled="busy">
        {{ busy ? 'Anmelden …' : 'Anmelden' }}
      </button>
    </form>
  </div>
</template>

<style scoped>
.login-wrap {
  display: grid;
  place-items: center;
  min-height: calc(100vh - 6rem);
}
.login {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  width: min(22rem, 90vw);
  padding: 2rem;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--bg-soft);
}
.login h1 {
  margin: 0;
  font-size: 1.2rem;
  text-align: center;
}
.hint {
  margin: 0;
  color: var(--text-dim);
  font-size: 0.85rem;
  text-align: center;
}
label {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.85rem;
  color: var(--text-dim);
}
input {
  font: inherit;
  padding: 0.45rem 0.7rem;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg);
  color: var(--text);
}
.error {
  margin: 0;
  color: var(--err);
  font-size: 0.85rem;
}
</style>
