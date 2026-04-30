import { useState } from 'react'
import { BookOpen } from 'lucide-react'
import { LoginForm } from './LoginForm'
import { RegisterForm } from './RegisterForm'

export const AuthCard = () => {
  const [mode, setMode] = useState<'login' | 'register'>('login')

  return (
    <div className="min-h-screen flex items-center justify-center px-4" style={{ background: 'var(--color-surface-0)' }}>
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="inline-flex p-3 rounded-xl mb-4" style={{ background: 'var(--color-accent-subtle)', border: '1px solid var(--color-accent-border)' }}>
            <BookOpen size={28} style={{ color: 'var(--color-accent)' }} />
          </div>
          <h1 style={{ fontFamily: 'var(--font-serif)', fontSize: '1.6rem', color: 'var(--color-text-primary)' }}>
            ScholarScan
          </h1>
          <p className="text-sm mt-1" style={{ color: 'var(--color-text-tertiary)' }}>
            AI-Powered Assessment
          </p>
        </div>

        <div className="surface-1 p-6">
          <div className="flex mb-6 rounded-lg overflow-hidden" style={{ background: 'var(--color-surface-2)', border: '1px solid var(--color-border)' }}>
            {(['login', 'register'] as const).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => setMode(m)}
                className="flex-1 py-2.5 text-sm font-medium capitalize transition-colors"
                style={{
                  background: mode === m ? 'var(--color-accent-subtle)' : 'transparent',
                  color: mode === m ? 'var(--color-accent)' : 'var(--color-text-tertiary)',
                }}
              >
                {m === 'login' ? 'Sign in' : 'Register'}
              </button>
            ))}
          </div>

          {mode === 'login' ? <LoginForm /> : <RegisterForm />}
        </div>

        <p className="text-center text-xs mt-4" style={{ color: 'var(--color-text-disabled)' }}>
          {mode === 'login' ? (
            <>Don&apos;t have an account?{' '}
              <button type="button" onClick={() => setMode('register')} className="underline" style={{ color: 'var(--color-accent)' }}>Register</button>
            </>
          ) : (
            <>Already have an account?{' '}
              <button type="button" onClick={() => setMode('login')} className="underline" style={{ color: 'var(--color-accent)' }}>Sign in</button>
            </>
          )}
        </p>
      </div>
    </div>
  )
}
