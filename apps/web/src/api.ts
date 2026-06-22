import { createApiClient } from '@knowlton/api-client'

const baseUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export const api = createApiClient({ baseUrl })
