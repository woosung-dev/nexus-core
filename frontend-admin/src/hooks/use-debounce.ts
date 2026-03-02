import * as React from "react"

/**
 * 값의 변경을 지연시키는 공통 훅.
 * 검색 Input 등에서 불필요한 API 호출을 방지하기 위해 사용한다.
 */
export function useDebounce<T>(value: T, delayMs: number): T {
  const [debouncedValue, setDebouncedValue] = React.useState<T>(value)

  React.useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delayMs)
    return () => clearTimeout(timer)
  }, [value, delayMs])

  return debouncedValue
}
