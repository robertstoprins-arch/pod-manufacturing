import { useAuth } from '@clerk/clerk-react'
import { useCallback } from 'react'
import { apiFetch } from './client'

/**
 * Returns an apiFetch wrapper that auto-injects the current Clerk JWT.
 * Use this in all authenticated pages instead of importing apiFetch directly.
 *
 * const api = useApi()
 * const data = await api('/materials')
 */
export function useApi() {
  const { getToken } = useAuth()

  return useCallback(async (path, opts = {}) => {
    const token = await getToken()
    return apiFetch(path, { ...opts, token })
  }, [getToken])
}
