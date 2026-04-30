interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
  readonly VITE_API_PORT?: string
  readonly VITE_AUTH_REQUIRED?: string
  readonly VITE_REFRESH_LEEWAY_SEC?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
