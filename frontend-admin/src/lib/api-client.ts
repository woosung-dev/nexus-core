import axios from "axios"

/**
 * Axios 커스텀 인스턴스.
 * 모든 API 호출은 이 인스턴스를 통해 수행한다.
 */
export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080",
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 10_000,
})

// 응답 인터셉터: 에러 로깅
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.detail ?? error.message ?? "알 수 없는 오류"
    console.error(`[API Error] ${error.config?.url} → ${message}`)
    return Promise.reject(error)
  }
)
