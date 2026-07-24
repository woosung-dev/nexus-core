"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useSignIn } from "@clerk/nextjs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Loader2 } from "lucide-react";

export function LoginForm() {
  const router = useRouter();
  const { signIn, isLoaded, setActive } = useSignIn();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [oauthLoading, setOauthLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loginMode, setLoginMode] = useState<"hanaro" | "email">("hanaro");
  const [hanaroId, setHanaroId] = useState("");
  const [hanaroPw, setHanaroPw] = useState("");

  // 이메일/비밀번호 로그인
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isLoaded) return;
    setIsLoading(true);
    setError(null);

    try {
      const result = await signIn.create({
        identifier: email,
        password,
      });

      if (result.status === "complete") {
        // setActive로 활성 세션을 즉시 반영(빠뜨리면 새로고침 전까지 비인증 상태).
        // beforeEmit에서 router.push를 호출해 navigation을 emit과 동기화한다.
        await setActive({
          session: result.createdSessionId,
          beforeEmit: () => router.push("/"),
        });
      }
    } catch {
      setError("이메일 또는 비밀번호가 올바르지 않습니다.");
    } finally {
      setIsLoading(false);
    }
  };

  // 하나로 SSO 로그인: 서버 라우트로 검증 → Clerk ticket 로그인
  const handleHanaroSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isLoaded) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/auth/hanaro", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ userid: hanaroId, password: hanaroPw }),
      });
      if (res.status === 429) {
        setError("로그인 시도가 너무 많습니다. 약 5분 후 다시 시도해 주세요.");
        return;
      }
      if (!res.ok) {
        setError("아이디 또는 비밀번호가 올바르지 않습니다.");
        return;
      }
      const { ticket } = (await res.json()) as { ticket: string; isOfficial: boolean };
      const result = await signIn.create({ strategy: "ticket", ticket });
      if (result.status === "complete") {
        await setActive({ session: result.createdSessionId, beforeEmit: () => router.push("/") });
      } else {
        setError("로그인 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.");
      }
    } catch {
      setError("로그인 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.");
    } finally {
      setIsLoading(false);
    }
  };

  // OAuth 소셜 로그인 (Google / Apple)
  const handleOAuthLogin = async (provider: "oauth_google" | "oauth_apple") => {
    if (!isLoaded) return;
    setOauthLoading(provider);
    setError(null);

    try {
      await signIn.authenticateWithRedirect({
        strategy: provider,
        redirectUrl: "/sso-callback",
        redirectUrlComplete: "/",
      });
    } catch {
      setError(`소셜 로그인에 실패했습니다. 다시 시도해 주세요.`);
      setOauthLoading(null);
    }
  };

  return (
    <Card className="w-full max-w-md bg-white/90 backdrop-blur-xl border border-amber-100 shadow-xl shadow-amber-500/5 relative overflow-hidden">
      {/* Subtle Glow Effect */}
      <div className="absolute -top-24 -left-24 w-48 h-48 bg-amber-500/10 rounded-full blur-[80px] pointer-events-none" />
      <div className="absolute -bottom-24 -right-24 w-48 h-48 bg-amber-500/10 rounded-full blur-[80px] pointer-events-none" />

      <CardHeader className="space-y-1 pb-6 z-10 relative">
        <CardTitle className="text-3xl font-bold tracking-tight text-center text-zinc-900">
          Welcome back
        </CardTitle>
        <CardDescription className="text-center text-zinc-500 w-full">
          이메일과 비밀번호를 입력하여 로그인하세요.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4 z-10 relative">
        <div id="clerk-captcha"></div>
        {/* 에러 메시지 */}
        {error && (
          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm text-center">
            {error}
          </div>
        )}

        <div className="flex gap-2 p-1 rounded-lg bg-zinc-100 mb-2">
          <button
            type="button"
            onClick={() => setLoginMode("hanaro")}
            className={`flex-1 h-9 rounded-md text-sm font-semibold transition-all ${loginMode === "hanaro" ? "bg-white text-zinc-900 shadow-sm" : "text-zinc-500"}`}
          >
            하나로 SSO
          </button>
          <button
            type="button"
            onClick={() => setLoginMode("email")}
            className={`flex-1 h-9 rounded-md text-sm font-semibold transition-all ${loginMode === "email" ? "bg-white text-zinc-900 shadow-sm" : "text-zinc-500"}`}
          >
            이메일
          </button>
        </div>

        {loginMode === "hanaro" && (
          <form onSubmit={handleHanaroSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="hanaroId" className="text-zinc-700 font-medium">하나로 아이디</Label>
              <Input id="hanaroId" type="text" placeholder="하나로 SSO 아이디" value={hanaroId}
                onChange={(e) => setHanaroId(e.target.value)} required disabled={isLoading}
                className="bg-zinc-50 border-zinc-200 text-zinc-900 focus-visible:ring-amber-500/30 focus-visible:border-amber-400 transition-all h-12 shadow-sm" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="hanaroPw" className="text-zinc-700 font-medium">비밀번호</Label>
              <Input id="hanaroPw" type="password" value={hanaroPw}
                onChange={(e) => setHanaroPw(e.target.value)} required disabled={isLoading}
                className="bg-zinc-50 border-zinc-200 text-zinc-900 focus-visible:ring-amber-500/30 focus-visible:border-amber-400 transition-all h-12 shadow-sm" />
            </div>
            <Button type="submit" disabled={isLoading}
              className="w-full h-12 bg-amber-500 hover:bg-amber-600 text-white font-bold text-md mt-6 transition-all shadow-md shadow-amber-500/20 hover:shadow-lg hover:shadow-amber-500/30">
              {isLoading ? <Loader2 className="h-5 w-5 animate-spin" /> : "하나로 SSO 로그인"}
            </Button>
          </form>
        )}

        {loginMode === "email" && (
          <>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email" className="text-zinc-700 font-medium">
              이메일 계정
            </Label>
            <Input
              id="email"
              type="email"
              placeholder="name@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={isLoading}
              className="bg-zinc-50 border-zinc-200 text-zinc-900 focus-visible:ring-amber-500/30 focus-visible:border-amber-400 transition-all h-12 shadow-sm"
            />
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="password" className="text-zinc-700 font-medium">
                비밀번호
              </Label>
              <Link
                href="/forgot-password"
                className="text-sm font-medium text-zinc-500 hover:text-amber-500 transition-colors"
                tabIndex={-1}
              >
                비밀번호를 잊으셨나요?
              </Link>
            </div>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={isLoading}
              className="bg-zinc-50 border-zinc-200 text-zinc-900 focus-visible:ring-amber-500/30 focus-visible:border-amber-400 transition-all h-12 shadow-sm"
            />
          </div>
          <Button
            type="submit"
            disabled={isLoading}
            className="w-full h-12 bg-amber-500 hover:bg-amber-600 text-white font-bold text-md mt-6 transition-all shadow-md shadow-amber-500/20 hover:shadow-lg hover:shadow-amber-500/30"
          >
            {isLoading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              "로그인"
            )}
          </Button>
        </form>

        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center">
            <span className="w-full border-t border-zinc-200" />
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-white px-2 text-zinc-400 font-semibold">
              Or continue with
            </span>
          </div>
        </div>

        <div className="flex flex-col gap-3">
          {/* Google 로그인 */}
          <Button
            variant="outline"
            disabled
            onClick={() => handleOAuthLogin("oauth_google")}
            className="w-full h-12 bg-white border border-zinc-200 hover:bg-zinc-50 hover:text-zinc-900 transition-all text-zinc-700 shadow-sm"
          >
            {oauthLoading === "oauth_google" ? (
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
            ) : (
              <svg
                viewBox="0 0 24 24"
                className="mr-2 h-5 w-5"
                aria-hidden="true"
              >
                <path
                  d="M12.0003 4.75C13.7703 4.75 15.3553 5.36002 16.6053 6.54998L20.0303 3.125C17.9502 1.19 15.2353 0 12.0003 0C7.31028 0 3.25527 2.69 1.28027 6.60998L5.27028 9.70498C6.21525 6.86002 8.87028 4.75 12.0003 4.75Z"
                  fill="#EA4335"
                />
                <path
                  d="M23.49 12.275C23.49 11.49 23.415 10.73 23.3 10H12V14.51H18.47C18.18 15.99 17.34 17.25 16.08 18.1L19.945 21.1C22.2 19.01 23.49 15.92 23.49 12.275Z"
                  fill="#4285F4"
                />
                <path
                  d="M5.26498 14.2949C5.02498 13.5699 4.88501 12.7999 4.88501 11.9999C4.88501 11.1999 5.01998 10.4299 5.26498 9.7049L1.275 6.60986C0.46 8.22986 0 10.0599 0 11.9999C0 13.9399 0.46 15.7699 1.28 17.3899L5.26498 14.2949Z"
                  fill="#FBBC05"
                />
                <path
                  d="M12.0004 24.0001C15.2404 24.0001 17.9654 22.935 19.9454 21.095L16.0804 18.095C15.0054 18.82 13.6204 19.245 12.0004 19.245C8.8704 19.245 6.21537 17.135 5.26537 14.29L1.27539 17.385C3.25539 21.31 7.3104 24.0001 12.0004 24.0001Z"
                  fill="#34A853"
                />
              </svg>
            )}
            Google 로그인
          </Button>

          {/* Apple 로그인 */}
          <Button
            variant="outline"
            disabled
            onClick={() => handleOAuthLogin("oauth_apple")}
            className="w-full h-12 bg-white border border-zinc-200 hover:bg-zinc-50 hover:text-zinc-900 transition-all text-zinc-700 shadow-sm"
          >
            {oauthLoading === "oauth_apple" ? (
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
            ) : (
              <svg
                viewBox="0 0 24 24"
                className="mr-2 h-5 w-5"
                aria-hidden="true"
                fill="currentColor"
              >
                <path d="M12.152 6.896c-.948 0-2.415-1.078-3.96-1.04-2.04.027-3.91 1.183-4.961 3.014-2.117 3.675-.546 9.103 1.519 12.09 1.013 1.454 2.208 3.09 3.792 3.039 1.52-.065 2.09-.987 3.935-.987 1.831 0 2.35.987 3.96.948 1.637-.026 2.676-1.48 3.676-2.948 1.156-1.688 1.636-3.325 1.662-3.415-.039-.013-3.182-1.221-3.22-4.857-.026-3.04 2.48-4.494 2.597-4.559-1.429-2.09-3.623-2.324-4.39-2.376-2-.156-3.675 1.09-4.61 1.09zM15.53 3.83c.843-1.012 1.4-2.427 1.245-3.83-1.207.052-2.662.805-3.532 1.818-.78.896-1.454 2.338-1.273 3.714 1.338.104 2.715-.688 3.559-1.701" />
              </svg>
            )}
            Apple 로그인
          </Button>
        </div>
          </>
        )}
      </CardContent>

      <CardFooter className="flex justify-center z-10 relative border-t border-zinc-100 pt-6 mt-2 pb-8">
        <p className="text-sm text-zinc-500 text-center">
          계정이 없으신가요?{" "}
          {/* OAuth 버튼과 마찬가지로 가입 흐름 임시 비활성화.
             * 추후 활성화 시 <Link href="/signup"> 로 복원. */}
          <span
            aria-disabled="true"
            className="text-zinc-400 font-semibold opacity-50 cursor-not-allowed select-none"
          >
            가입하기
          </span>
        </p>
      </CardFooter>
    </Card>
  );
}
