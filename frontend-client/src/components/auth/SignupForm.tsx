"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Loader2 } from "lucide-react";
import { createClient } from "@/lib/supabase/client";

export function SignupForm() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [agreeTerms, setAgreeTerms] = useState<boolean | "indeterminate">(
    false
  );
  const [isLoading, setIsLoading] = useState(false);
  const [oauthLoading, setOauthLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // 이메일/비밀번호 회원가입
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError("비밀번호가 일치하지 않습니다.");
      return;
    }

    if (!agreeTerms) {
      setError("이용약관에 동의해 주세요.");
      return;
    }

    setIsLoading(true);
    const supabase = createClient();
    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo: `${window.location.origin}/auth/callback`,
      },
    });

    if (error) {
      setError(error.message);
      setIsLoading(false);
      return;
    }

    setSuccess(true);
    setIsLoading(false);
  };

  // OAuth 소셜 로그인 (회원가입과 동일하게 동작)
  const handleOAuthSignup = async (provider: "kakao" | "google") => {
    setOauthLoading(provider);
    setError(null);

    const supabase = createClient();
    const { error } = await supabase.auth.signInWithOAuth({
      provider,
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    });

    if (error) {
      setError(`${provider} 회원가입에 실패했습니다. 다시 시도해 주세요.`);
      setOauthLoading(null);
    }
  };

  // 이메일 인증 안내 화면
  if (success) {
    return (
      <Card className="w-full max-w-md bg-zinc-950/80 backdrop-blur-xl border-zinc-800 shadow-2xl relative overflow-hidden">
        <div className="absolute -top-32 -right-32 w-64 h-64 bg-green-500/10 rounded-full blur-[100px] pointer-events-none" />
        <CardHeader className="space-y-1 pb-6 z-10 relative">
          <CardTitle className="text-3xl font-bold tracking-tight text-center text-foreground">
            ✉️ 이메일을 확인해 주세요
          </CardTitle>
          <CardDescription className="text-center text-muted-foreground w-full pt-2">
            <strong className="text-zinc-200">{email}</strong>으로 인증
            메일을 발송했습니다.
            <br />
            메일의 링크를 클릭하면 가입이 완료됩니다.
          </CardDescription>
        </CardHeader>
        <CardFooter className="flex justify-center z-10 relative pb-8">
          <Button
            variant="outline"
            onClick={() => router.push("/login")}
            className="border-zinc-800 hover:bg-zinc-800"
          >
            로그인 페이지로 이동
          </Button>
        </CardFooter>
      </Card>
    );
  }

  return (
    <Card className="w-full max-w-md bg-zinc-950/80 backdrop-blur-xl border-zinc-800 shadow-2xl relative overflow-hidden">
      {/* Subtle Glow Effect */}
      <div className="absolute -top-32 -right-32 w-64 h-64 bg-amber-500/10 rounded-full blur-[100px] pointer-events-none" />
      <div className="absolute -bottom-32 -left-32 w-64 h-64 bg-blue-500/10 rounded-full blur-[100px] pointer-events-none" />

      <CardHeader className="space-y-1 pb-6 z-10 relative">
        <CardTitle className="text-3xl font-bold tracking-tight text-center text-foreground">
          Create an account
        </CardTitle>
        <CardDescription className="text-center text-muted-foreground w-full">
          AI Chat Hub의 모든 기능을 이용하기 위해
          <br className="hidden sm:block" />
          간단한 정보를 입력해 주세요.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4 z-10 relative">
        {/* 에러 메시지 */}
        {error && (
          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm text-center">
            {error}
          </div>
        )}

        {/* 소셜 로그인 (상단) */}
        <div className="flex flex-col gap-3">
          <Button
            variant="outline"
            disabled={!!oauthLoading}
            onClick={() => handleOAuthSignup("google")}
            className="w-full h-12 bg-zinc-900/30 border-zinc-800 hover:bg-zinc-800 hover:text-white transition-all text-zinc-300"
          >
            {oauthLoading === "google" ? (
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
            Google로 시작하기
          </Button>

          <Button
            variant="outline"
            disabled={!!oauthLoading}
            onClick={() => handleOAuthSignup("kakao")}
            className="w-full h-12 bg-[#FEE500]/10 border-[#FEE500]/30 hover:bg-[#FEE500]/20 hover:text-[#3C1E1E] transition-all text-[#FEE500]"
          >
            {oauthLoading === "kakao" ? (
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
            ) : (
              <svg
                viewBox="0 0 24 24"
                className="mr-2 h-5 w-5"
                aria-hidden="true"
              >
                <path
                  d="M12 3C6.477 3 2 6.463 2 10.691c0 2.734 1.811 5.126 4.535 6.482l-.927 3.428a.285.285 0 0 0 .434.301l3.976-2.622a14.09 14.09 0 0 0 1.982.14c5.523 0 10-3.463 10-7.729S17.523 3 12 3z"
                  fill="currentColor"
                />
              </svg>
            )}
            Kakao로 시작하기
          </Button>
        </div>

        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center">
            <span className="w-full border-t border-zinc-800" />
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-zinc-950 px-2 text-muted-foreground">
              Or sign up with email
            </span>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-2">
            <Label htmlFor="email" className="text-zinc-300">
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
              className="bg-zinc-900/50 border-zinc-800 focus-visible:ring-amber-500/50 focus-visible:border-amber-500 transition-all h-12"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="password" className="text-zinc-300">
              비밀번호
            </Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={isLoading}
              className="bg-zinc-900/50 border-zinc-800 focus-visible:ring-amber-500/50 focus-visible:border-amber-500 transition-all h-12"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="confirmPassword" className="text-zinc-300">
              비밀번호 확인
            </Label>
            <Input
              id="confirmPassword"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              disabled={isLoading}
              className="bg-zinc-900/50 border-zinc-800 focus-visible:ring-amber-500/50 focus-visible:border-amber-500 transition-all h-12"
            />
          </div>

          <div className="flex items-start space-x-3 pt-2">
            <Checkbox
              id="terms"
              checked={agreeTerms}
              onCheckedChange={setAgreeTerms}
              className="data-[state=checked]:bg-amber-500 data-[state=checked]:border-amber-500 border-zinc-600 mt-1"
            />
            <div className="grid leading-tight max-w-[90%]">
              <label
                htmlFor="terms"
                className="text-sm font-medium text-zinc-300 peer-disabled:cursor-not-allowed peer-disabled:opacity-70 leading-relaxed cursor-pointer select-none"
              >
                서비스 이용약관 및 개인정보 처리방침에 동의합니다.
              </label>
            </div>
          </div>

          <Button
            type="submit"
            disabled={isLoading}
            className="w-full h-12 bg-amber-500 hover:bg-amber-600 text-black font-bold text-md mt-6 transition-all shadow-[0_0_15px_rgba(245,158,11,0.3)] hover:shadow-[0_0_25px_rgba(245,158,11,0.5)]"
          >
            {isLoading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              "회원가입 완료"
            )}
          </Button>
        </form>
      </CardContent>

      <CardFooter className="flex justify-center z-10 relative border-t border-border/40 pt-6 mt-2 pb-8">
        <p className="text-sm text-muted-foreground text-center">
          이미 계정이 있으신가요?{" "}
          <Link
            href="/login"
            className="text-amber-500 font-semibold hover:text-amber-400 hover:underline underline-offset-4 transition-all"
          >
            로그인
          </Link>
        </p>
      </CardFooter>
    </Card>
  );
}
