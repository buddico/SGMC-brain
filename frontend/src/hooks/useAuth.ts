import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import type { AuthUser } from '@/api/types'

export function useAuth() {
  const { data: user, isLoading, error } = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: () => api<AuthUser>('/auth/me'),
  })

  return { user, isLoading, error }
}
