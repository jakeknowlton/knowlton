<script setup lang="ts">
import { ref } from 'vue';
import type { LaundryLoadRead } from '@knowlton/api-client';
import {
  LAUNDRY_STATUSES,
  statusLabel,
  type LaundryStatus,
} from '@knowlton/shared';

const DEFAULT_DURATION_MINUTES = 45;

defineProps<{
  load: LaundryLoadRead;
  countdown: string | null;
}>();

const emit = defineEmits<{
  statusChange: [change: { status: LaundryStatus; durationMinutes: number }];
  delete: [];
}>();

const durationMinutes = ref(DEFAULT_DURATION_MINUTES);

function statusFrom(event: Event): LaundryStatus {
  return (event.target as HTMLSelectElement).value as LaundryStatus;
}

function durationFrom(event: Event) {
  const value = Number((event.target as HTMLInputElement).value);
  durationMinutes.value = Number.isFinite(value)
    ? Math.max(1, value)
    : DEFAULT_DURATION_MINUTES;
}

function changeStatus(event: Event) {
  emit('statusChange', {
    status: statusFrom(event),
    durationMinutes: durationMinutes.value,
  });
}
</script>

<template>
  <li>
    <strong>{{ load.label ?? `Load #${load.id}` }}</strong>

    <select :value="load.status" @change="changeStatus">
      <option v-for="status in LAUNDRY_STATUSES" :key="status" :value="status">
        {{ statusLabel(status) }}
      </option>
    </select>

    <label>
      mins
      <input
        type="number"
        min="1"
        :value="durationMinutes"
        @input="durationFrom"
      />
    </label>

    <span v-if="countdown">Timer {{ countdown }}</span>

    <button type="button" @click="emit('delete')">Delete</button>
  </li>
</template>
