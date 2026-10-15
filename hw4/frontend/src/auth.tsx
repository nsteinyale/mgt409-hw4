import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import * as api from './api'

interface AuthState {
  user: api.User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  signup: (input: api.SignupInput) => Promise<void>
  logout: () => Promise<void>
  refresh: () => Promise<void> // re-read the user (e.g. after their saved size changes)
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<api.User | null>(null)
  const [loading, setLoading] = useState(true)

  // On page load, ask the backend who is logged in (based on the session cookie).
  useEffect(() => {
    api
      .fetchCurrentUser()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  const value: AuthState = {
    user,
    loading,
    login: async (email, password) => setUser(await api.login(email, password)),
    signup: async (input) => setUser(await api.signup(input)),
    logout: async () => {
      await api.logout()
      setUser(null)
    },
    refresh: async () => setUser(await api.fetchCurrentUser()),
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
