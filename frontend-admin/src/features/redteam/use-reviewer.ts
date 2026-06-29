"use client"

/**
 * 리뷰어 신원 관리 훅.
 * 인증이 없는 admin이므로, 최대 3명의 리뷰어 슬롯 이름과 "현재 나"를 localStorage로 관리한다.
 */
import * as React from "react"
import {
  DEFAULT_REVIEWER_NAMES,
  REVIEWER_ACTIVE_KEY,
  REVIEWER_NAMES_KEY,
  REVIEWER_SLOT_COUNT,
} from "./constants"

export function useReviewer() {
  const [names, setNames] = React.useState<string[]>(DEFAULT_REVIEWER_NAMES)
  const [activeIndex, setActiveIndex] = React.useState(0)
  const [hydrated, setHydrated] = React.useState(false)

  // 초기 로드 (클라이언트 전용)
  React.useEffect(() => {
    try {
      const rawNames = localStorage.getItem(REVIEWER_NAMES_KEY)
      if (rawNames) {
        const parsed = JSON.parse(rawNames)
        if (Array.isArray(parsed) && parsed.length === REVIEWER_SLOT_COUNT) {
          setNames(parsed.map((n) => String(n)))
        }
      }
      const rawActive = localStorage.getItem(REVIEWER_ACTIVE_KEY)
      if (rawActive) {
        const idx = Number(rawActive)
        if (idx >= 0 && idx < REVIEWER_SLOT_COUNT) setActiveIndex(idx)
      }
    } catch {
      /* ignore */
    }
    setHydrated(true)
  }, [])

  const updateName = React.useCallback((index: number, name: string) => {
    setNames((prev) => {
      const next = [...prev]
      next[index] = name
      localStorage.setItem(REVIEWER_NAMES_KEY, JSON.stringify(next))
      return next
    })
  }, [])

  const selectActive = React.useCallback((index: number) => {
    setActiveIndex(index)
    localStorage.setItem(REVIEWER_ACTIVE_KEY, String(index))
  }, [])

  const activeName = names[activeIndex] ?? DEFAULT_REVIEWER_NAMES[0]

  return { names, activeIndex, activeName, hydrated, updateName, selectActive }
}
