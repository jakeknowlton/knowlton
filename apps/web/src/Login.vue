<script setup lang="ts">
import { ref } from 'vue'
import { ApiError } from '@knowlton/api-client'
import { api } from './api'

type Mode = 'login' | 'register'

const username = ref('')
const password = ref('')
const error = ref<string | null>(null)
const busy = ref(false)

function message(e: unknown): string {
  return e instanceof ApiError ? e.detail : 'Something went wrong'
}

async function submit(mode: Mode) {
  error.value = null
  busy.value = true

  try {
    if (mode === 'register') {
      await api.auth.register({ username: username.value, password: password.value })
    }

    await api.auth.login({ username: username.value, password: password.value })
  } catch (e) {
    error.value = message(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <main>
    <h1>Sign in</h1>

    <form @submit.prevent="submit('login')">
      <label>
        Username
        <input v-model="username" autocomplete="username" required />
      </label>

      <label>
        Password
        <input v-model="password" type="password" autocomplete="current-password" required />
      </label>

      <div>
        <button type="submit" :disabled="busy">Log in</button>
        <button type="button" :disabled="busy" @click="submit('register')">Register</button>
      </div>
    </form>

    <p v-if="error" role="alert">{{ error }}</p>
  </main>
</template>
