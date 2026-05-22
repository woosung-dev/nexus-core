import type { Metadata } from "next";
import { AuthenticateWithRedirectCallback } from "@clerk/nextjs";

export const metadata: Metadata = {
  title: "로그인 처리 중",
  robots: { index: false, follow: false },
};

export default function SSOCallbackPage() {
  return <AuthenticateWithRedirectCallback />;
}
