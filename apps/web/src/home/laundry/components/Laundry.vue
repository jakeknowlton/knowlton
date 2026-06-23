<script setup lang="ts">
import { api } from '../../../shared/api/client';
import LaundryLoadRow from './LaundryLoadRow.vue';
import { useLaundryLoads } from '../composables/useLaundryLoads';

const {
  loads,
  error,
  newLabel,
  createLoad,
  changeStatus,
  deleteLoad,
  countdown,
} = useLaundryLoads();

function logout() {
  void api.auth.logout();
}
</script>

<template>
  <main>
    <header>
      <h1>Laundry</h1>
      <button type="button" @click="logout">Log out</button>
    </header>

    <form @submit.prevent="createLoad">
      <input v-model="newLabel" placeholder="New load label (optional)" />
      <button type="submit">Add load</button>
    </form>

    <p v-if="error" role="alert">{{ error }}</p>

    <p v-if="loads.length === 0">No loads yet.</p>

    <ul v-else>
      <LaundryLoadRow
        v-for="load in loads"
        :key="load.id"
        :load="load"
        :countdown="countdown(load)"
        @status-change="
          changeStatus(load, $event.status, $event.durationMinutes)
        "
        @delete="deleteLoad(load)"
      />
    </ul>
  </main>
</template>
