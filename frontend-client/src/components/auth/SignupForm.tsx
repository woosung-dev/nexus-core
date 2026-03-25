"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useSignUp } from "@clerk/nextjs";
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

export function SignupForm() {
  const router = useRouter();
  const { signUp, isLoaded } = useSignUp();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [agreeTerms, setAgreeTerms] = useState<boolean | "indeterminate">(false);
  const [isLoading, setIsLoading] = useState(false);
  const [oauthLoading, setOauthLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [otpStep, setOtpStep] = useState(false);
  const [otpCode, setOtpCode] = useState("");

  // 이메일/비밀번호 회원가입
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isLoaded) return;
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
    try {
      await signUp.create({ emailAddress: email, password });
      await signUp.prepareEmailAddressVerification({ strategy: "email_code" });
      setOtpStep(true);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "회원가입에 실패했습니다.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  // OTP 인증 완료
  const handleOtpVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isLoaded) return;
    setIsLoading(true);
    setError(null);

    try {
      const result = await signUp.attemptEmailAddressVerification({
        code: otpCode,
      });
      if (result.status === "complete") {
        router.push("/");
        router.refresh();
      }
    } catch {
      setError("인증 코드가 올바르지 않습니다. 다시 확인해 주세요.");
    } finally {
      setIsLoading(false);
    }
  };

  // OAuth 소셜 회원가입 (Google / Apple)
  const handleOAuthSignup = async (
    provider: "oauth_google" | "oauth_apple"
  ) => {
    if (!isLoaded) return;
    setOauthLoading(provider);
    setError(null);

    try {
      await signUp.authenticateWithRedirect({
        strategy: provider,
        redirectUrl: "/sso-callback",
        redirectUrlComplete: "/",
      });
    } catch {
      setError("소셜 회원가입에 실패했습니다. 다시 시도해 주세요.");
      setOauthLoading(null);
    }
  };

  // OTP 입력 화면
  if (otpStep) {
    return (
      <Card className="w-full max-w-md bg-zinc-950/80 backdrop-blur-xl border-zinc-800 shadow-2xl relative overflow-hidden">
        <div className="absolute -top-32 -right-32 w-64 h-64 bg-green-500/10 rounded-full blur-[100px] pointer-events-none" />
        <CardHeader className="space-y-1 pb-6 z-10 relative">
          <CardTitle className="text-3xl font-bold tracking-tight text-center text-foreground">
            이메일 인증
          </CardTitle>
          <CardDescription className="text-center text-muted-foreground w-full pt-2">
            <strong className="text-zinc-200">{email}</strong>으로 전송된
            <br />
            6자리 인증 코드를 입력해 주세요.
          </CardDescription>
        </CardHeader>
        <CardContent className="z-10 relative">
          {error && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm text-center mb-4">
              {error}
            </div>
          )}
          <form onSubmit={handleOtpVerify} className="space-y-4">
            <Input
              type="text"
              placeholder="인증 코드 6자리"
              value={otpCode}
              onChange={(e) => setOtpCode(e.target.value)}
              maxLength={6}
              required
              disabled={isLoading}
              className="bg-zinc-900/50 border-zinc-800 text-center text-2xl tracking-widest h-14"
            />
            <Button
              type="submit"
              disabled={isLoading}
              className="w-full h-12 bg-amber-500 hover:bg-amber-600 text-black font-bold"
            >
              {isLoading ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                "인증 완료"
              )}
            </Button>
          </form>
        </CardContent>
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
        <div id="clerk-captcha"></div>
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
            onClick={() => handleOAuthSignup("oauth_google")}
            className="w-full h-12 bg-zinc-900/30 border-zinc-800 hover:bg-zinc-800 hover:text-white transition-all text-zinc-300"
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
            Google로 시작하기
          </Button>

          <Button
            variant="outline"
            disabled={!!oauthLoading}
            onClick={() => handleOAuthSignup("oauth_apple")}
            className="w-full h-12 bg-zinc-900/30 border-zinc-800 hover:bg-zinc-800 hover:text-white transition-all text-zinc-300"
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
            Apple로 시작하기
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
