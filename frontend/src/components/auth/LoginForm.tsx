import { useState } from 'react'
import { LogIn, Loader2, AlertTriangle } from 'lucide-react'
import { useAuth } from '../../auth/useAuth'

export const LoginForm = () => {
  const { login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="login-email" className="block text-xs font-medium mb-1.5" style={{ color: 'var(--color-text-tertiary)' }}>
          Email
        </label>
        <input
          id="login-email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@school.edu"
          required
          autoComplete="email"
          className="input-base"
        />
      </div>
      <div>
        <label htmlFor="login-password" className="block text-xs font-medium mb-1.5" style={{ color: 'var(--color-text-tertiary)' }}>
          Password
        </label>
        <input
          id="login-password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="••••••••"
          required
          autoComplete="current-password"
          className="input-base"
        />
      </div>

      {error && (
        <div className="flex items-center gap-2 text-xs p-2.5 rounded-lg" style={{ background: 'var(--color-error-subtle)', color: 'var(--color-error)' }}>
          <AlertTriangle size={14} />
          {error}
        </div>
      )}

      <button type="submit" disabled={loading || !email || !password} className="btn-primary w-full flex items-center justify-center gap-2">
        {loading ? <Loader2 size={16} className="animate-spin" /> : <LogIn size={16} />}
        {loading ? 'Signing in…' : 'Sign in'}
      </button>
    </form>
  )
}
