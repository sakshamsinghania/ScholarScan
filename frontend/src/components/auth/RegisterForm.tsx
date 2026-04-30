import { useState } from 'react'
import { UserPlus, Loader2, AlertTriangle } from 'lucide-react'
import { useAuth } from '../../auth/useAuth'

export const RegisterForm = () => {
  const { register } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<'teacher' | 'admin'>('teacher')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const passwordValid = password.length >= 8

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!passwordValid) {
      setError('Password must be at least 8 characters')
      return
    }
    setError('')
    setLoading(true)
    try {
      await register(email, password, role)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="register-email" className="block text-xs font-medium mb-1.5" style={{ color: 'var(--color-text-tertiary)' }}>
          Email
        </label>
        <input
          id="register-email"
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
        <label htmlFor="register-password" className="block text-xs font-medium mb-1.5" style={{ color: 'var(--color-text-tertiary)' }}>
          Password
        </label>
        <input
          id="register-password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Min 8 characters"
          required
          minLength={8}
          autoComplete="new-password"
          className="input-base"
        />
        {password && !passwordValid && (
          <p className="text-xs mt-1" style={{ color: 'var(--color-error)' }}>
            At least 8 characters required
          </p>
        )}
      </div>
      <div>
        <label htmlFor="register-role" className="block text-xs font-medium mb-1.5" style={{ color: 'var(--color-text-tertiary)' }}>
          Role
        </label>
        <div className="flex gap-2">
          {(['teacher', 'admin'] as const).map((r) => (
            <button
              key={r}
              type="button"
              onClick={() => setRole(r)}
              className="flex-1 py-2 px-3 rounded-lg text-sm capitalize transition-colors"
              style={{
                background: role === r ? 'var(--color-accent-subtle)' : 'var(--color-surface-2)',
                color: role === r ? 'var(--color-accent)' : 'var(--color-text-tertiary)',
                border: `1px solid ${role === r ? 'var(--color-accent-border)' : 'var(--color-border)'}`,
              }}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 text-xs p-2.5 rounded-lg" style={{ background: 'var(--color-error-subtle)', color: 'var(--color-error)' }}>
          <AlertTriangle size={14} />
          {error}
        </div>
      )}

      <button type="submit" disabled={loading || !email || !passwordValid} className="btn-primary w-full flex items-center justify-center gap-2">
        {loading ? <Loader2 size={16} className="animate-spin" /> : <UserPlus size={16} />}
        {loading ? 'Creating account…' : 'Create account'}
      </button>
    </form>
  )
}
