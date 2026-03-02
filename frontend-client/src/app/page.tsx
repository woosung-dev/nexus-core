import { LandingClient } from '@/components/landing/LandingClient';

// 랜딩 페이지 전체의 기본 재검증 주기 설정 (60초)
export const revalidate = 60;

export default function LandingPage() {
  return <LandingClient />;
}
