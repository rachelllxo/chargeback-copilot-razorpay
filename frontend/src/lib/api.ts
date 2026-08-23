import { useCallback, useEffect, useRef, useState } from 'react'

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(path, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    })
  } catch {
    throw new ApiError('Could not reach the investigation service.', 0)
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status})`
    try {
      const body = await res.json()
      if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : detail
    } catch {
      /* keep default */
    }
    throw new ApiError(detail, res.status)
  }
  return (await res.json()) as T
}

export const api = {
  get: <T,>(path: string) => request<T>(path),
  post: <T,>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body: JSON.stringify(body ?? {}) }),
}

interface AsyncState<T> {
  data: T | null
  loading: boolean
  error: string | null
  reload: () => void
}

/** Fetch helper with loading / error / empty handling for every async view. */
export function useApi<T>(path: string | null, deps: unknown[] = []): AsyncState<T> {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(Boolean(path))
  const [error, setError] = useState<string | null>(null)
  const [nonce, setNonce] = useState(0)
  const active = useRef(true)

  useEffect(() => {
    active.current = true
    if (!path) {
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    api
      .get<T>(path)
      .then((res) => {
        if (active.current) {
          setData(res)
          setLoading(false)
        }
      })
      .catch((err: ApiError) => {
        if (active.current) {
          setError(err.message)
          setLoading(false)
        }
      })
    return () => {
      active.current = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, nonce, ...deps])

  const reload = useCallback(() => setNonce((n) => n + 1), [])
  return { data, loading, error, reload }
}
