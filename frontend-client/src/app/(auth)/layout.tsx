import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";

export default async function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { userId } = await auth();

  // 이미 로그인된 유저는 메인으로 리다이렉트
  if (userId) {
    redirect("/");
  }

  return <>{children}</>;
}
