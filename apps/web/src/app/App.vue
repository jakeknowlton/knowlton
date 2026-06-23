<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue';
import { api } from '../shared/api/client';
import LoginView from '../auth/components/LoginView.vue';
import LaundryView from '../home/laundry/components/LaundryView.vue';

type SessionStatus = 'loading' | 'authenticated' | 'anonymous';

const session = ref<SessionStatus>('loading');

let unsubscribe: (() => void) | undefined;

onMounted(() => {
  unsubscribe = api.auth.subscribe((authenticated) => {
    session.value = authenticated ? 'authenticated' : 'anonymous';
  });

  api.auth
    .restore()
    .then((restored) => {
      session.value = restored ? 'authenticated' : 'anonymous';
    })
    .catch(() => {
      session.value = 'anonymous';
    });
});

onUnmounted(() => {
  unsubscribe?.();
});
</script>

<template>
  <main v-if="session === 'loading'">
    <p>Loading...</p>
  </main>
  <LaundryView v-else-if="session === 'authenticated'" />
  <LoginView v-else />
</template>
