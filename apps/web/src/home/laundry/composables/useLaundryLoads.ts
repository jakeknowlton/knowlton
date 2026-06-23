import { onMounted, onUnmounted, ref } from 'vue'
import type { LaundryLoadRead, LaundryLoadUpdate } from '@knowlton/api-client'
import {
  formatDuration,
  machineFor,
  remainingSeconds,
  type LaundryStatus,
} from '@knowlton/shared'
import { api } from '../../../shared/api/client'
import { errorMessage } from '../../../shared/errors/messages'

export function useLaundryLoads() {
  const loads = ref<LaundryLoadRead[]>([])
  const error = ref<string | null>(null)
  const newLabel = ref('')
  const now = ref(Date.now())

  async function run(action: () => Promise<void>) {
    try {
      await action()
      error.value = null
    } catch (e) {
      error.value = errorMessage(e)
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

  async function changeStatus(
    load: LaundryLoadRead,
    status: LaundryStatus,
    durationMinutes: number,
  ) {
    const patch: LaundryLoadUpdate = { status }
    const minutes = Math.max(1, durationMinutes)

    if (status === 'washing') patch.washer_duration_minutes = minutes
    if (status === 'drying') patch.dryer_duration_minutes = minutes

    await run(async () => {
      await api.laundry.update(load.id, patch)
      await refreshLoads()
    })
  }

  async function deleteLoad(load: LaundryLoadRead) {
    await run(async () => {
      await api.laundry.remove(load.id)
      await refreshLoads()
    })
  }

  function countdown(load: LaundryLoadRead): string | null {
    const machine = machineFor(load.status)
    if (!machine) return null

    const finish = machine === 'washer' ? load.washer_finish : load.dryer_finish
    const seconds = remainingSeconds(finish, now.value)
    return seconds === null ? null : formatDuration(seconds)
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

  return {
    loads,
    error,
    newLabel,
    createLoad,
    changeStatus,
    deleteLoad,
    countdown,
  }
}
