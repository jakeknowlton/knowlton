<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { ApiError, type LaundryLoad, type LaundryLoadUpdate } from '@knowlton/api-client'
import {
  LAUNDRY_STATUSES,
  formatDuration,
  machineFor,
  remainingSeconds,
  statusLabel,
  type LaundryStatus,
} from '@knowlton/shared'
import { api } from './api'

const DEFAULT_DURATION_MINUTES = 45

const loads = ref<LaundryLoad[]>([])
const error = ref<string | null>(null)
const newLabel = ref('')
const durations = ref<Record<number, number>>({})
const now = ref(Date.now())

function message(e: unknown): string {
  return e instanceof ApiError ? e.detail : 'Request failed'
}

async function run(action: () => Promise<void>) {
  try {
    await action()
    error.value = null
  } catch (e) {
    error.value = message(e)
  }
}

async function refreshLoads() {
  loads.value = await api.laundry.list()
}

async function createLoad() {
  await run(async () => {
    await api.laundry.create({ label: newLabel.value.trim() || null })
    newLabel.value = ''
    await refreshLoads()
  })
}

async function changeStatus(load: LaundryLoad, status: LaundryStatus) {
  const patch: LaundryLoadUpdate = { status }
  const minutes = Math.max(1, durations.value[load.id] ?? DEFAULT_DURATION_MINUTES)

  if (status === 'washing') patch.washer_duration_minutes = minutes
  if (status === 'drying') patch.dryer_duration_minutes = minutes

  await run(async () => {
    await api.laundry.update(load.id, patch)
    await refreshLoads()
  })
}

async function deleteLoad(load: LaundryLoad) {
  await run(async () => {
    await api.laundry.remove(load.id)
    await refreshLoads()
  })
}

function countdown(load: LaundryLoad): string | null {
  const machine = machineFor(load.status)
  if (!machine) return null

  const finish = machine === 'washer' ? load.washer_finish : load.dryer_finish
  const seconds = remainingSeconds(finish, now.value)
  return seconds === null ? null : formatDuration(seconds)
}

function statusFrom(event: Event): LaundryStatus {
  return (event.target as HTMLSelectElement).value as LaundryStatus
}

function setDuration(id: number, event: Event) {
  durations.value[id] = Number((event.target as HTMLInputElement).value)
}

let timer: number | undefined

onMounted(() => {
  void run(refreshLoads)
  timer = window.setInterval(() => {
    now.value = Date.now()
  }, 1000)
})

onUnmounted(() => {
  window.clearInterval(timer)
})
</script>

<template>
  <main>
    <header>
      <h1>Laundry</h1>
      <button type="button" @click="api.auth.logout()">Log out</button>
    </header>

    <form @submit.prevent="createLoad">
      <input v-model="newLabel" placeholder="New load label (optional)" />
      <button type="submit">Add load</button>
    </form>

    <p v-if="error" role="alert">{{ error }}</p>

    <p v-if="loads.length === 0">No loads yet.</p>

    <ul v-else>
      <li v-for="load in loads" :key="load.id">
        <strong>{{ load.label ?? `Load #${load.id}` }}</strong>

        <select :value="load.status" @change="changeStatus(load, statusFrom($event))">
          <option v-for="status in LAUNDRY_STATUSES" :key="status" :value="status">
            {{ statusLabel(status) }}
          </option>
        </select>

        <label>
          mins
          <input
            type="number"
            min="1"
            :value="durations[load.id] ?? DEFAULT_DURATION_MINUTES"
            @input="setDuration(load.id, $event)"
          />
        </label>

        <span v-if="countdown(load)">Timer {{ countdown(load) }}</span>

        <button type="button" @click="deleteLoad(load)">Delete</button>
      </li>
    </ul>
  </main>
</template>
