export interface UserPublic {
  id: string
  email: string
  role: 'teacher' | 'admin'
  created_at: string
}

export interface AuthTokens {
  access_token: string
  refresh_token: string
}

export interface AuthResponse extends AuthTokens {
  user: UserPublic
}

export interface RefreshResponse {
  access_token: string
}

export type AuthStatus = 'loading' | 'anon' | 'authed'
