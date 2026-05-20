// 단일 catch-all chat 페이지 — Gemini 스타일 in-place URL 전환의 핵심.
// URL 패턴 3가지를 모두 받아 처리한다:
//   /chat            → 빈 상태 안내
//   /chat/{id}       → 기존 세션 로드
//   /chat/new/{bot}  → POST /chats → 받은 id 로 history.replaceState (route navigation 없음)
// 실제 chat UI 는 ChatLayout 이 useChatStore.activeSessionId 를 구독해서 렌더한다.
"use client";

import { useEffect, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { Loader2, Sparkles } from "lucide-react";

import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { useChatStore } from "@/store/useChatStore";
import { ChatSessionListResponse, ChatSessionResponse } from "@/types/api";

type Intent =
  | { kind: "session"; id: string }
  | { kind: "new"; botId: string }
  | { kind: "empty" };

function parseIntent(slug: string[] | undefined): Intent {
  const segments = slug ?? [];
  if (segments.length === 1 && /^\d+$/.test(segments[0])) {
    return { kind: "session", id: segments[0] };
  }
  if (segments.length === 2 && segments[0] === "new") {
    return { kind: "new", botId: segments[1] };
  }
  return { kind: "empty" };
}

export default function ChatCatchAllPage() {
  const params = useParams<{ slug?: string[] }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const setActiveSessionId = useChatStore((s) => s.setActiveSessionId);
  // StrictMode 의 effect 중복 실행으로 세션이 두 번 생성되지 않도록 가드.
  const creatingForBotRef = useRef<string | null>(null);

  const intent = parseIntent(params?.slug);

  useEffect(() => {
    if (intent.kind === "session") {
      setActiveSessionId(intent.id);
      return;
    }

    if (intent.kind === "empty") {
      setActiveSessionId(null);
      return;
    }

    // intent.kind === "new" — POST /chats 후 history.replaceState 로 URL 만 갱신
    if (creatingForBotRef.current === intent.botId) return;
    creatingForBotRef.current = intent.botId;
    setActiveSessionId(null); // 생성 중에는 일시적으로 비활성 (Loader 표시)

    api
      .post<ChatSessionResponse>(`/chats?bot_id=${intent.botId}`)
      .then((res) => {
        const created = res.data;

        // 사이드바 캐시 prepend (idempotent precreate 가 같은 세션 반환 시 dedupe)
        queryClient.setQueryData<ChatSessionListResponse>(
          ["chats"],
          (old) => {
            if (!old) return { sessions: [created], total: 1 };
            const filtered = old.sessions.filter((s) => s.id !== created.id);
            const wasNew = filtered.length === old.sessions.length;
            return {
              sessions: [created, ...filtered],
              total: wasNew ? old.total + 1 : old.total,
            };
          },
        );

        // ★ 핵심: history.replaceState 로 URL 만 변경 — Next.js 의 라우트 mount 는 그대로 유지.
        // 이 catch-all 페이지가 mount 된 상태에서 URL 만 silent 갱신된다.
        window.history.replaceState({}, "", `/chat/${created.id}`);
        setActiveSessionId(String(created.id));
      })
      .catch((err) => {
        console.error("Failed to create chat session:", err);
        creatingForBotRef.current = null; // 재시도 가능
        router.replace("/");
      });
  // params 변화 시 재평가 (sidebar 클릭 등 라우트 이동 케이스). history.replaceState 는 params 갱신하지 않음.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params?.slug?.join("/")]);

  // ChatLayout 의 children 으로 전달되어 activeSessionId 가 비어 있을 때만 표시된다.
  if (intent.kind === "new") {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-3 text-zinc-400 bg-linear-to-b from-sky-50/50 via-white to-white">
        <Loader2 className="w-6 h-6 animate-spin text-amber-500" />
        <span className="text-sm font-medium">대화를 준비하고 있어요…</span>
      </div>
    );
  }

  if (intent.kind === "empty") {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-linear-to-b from-sky-50/50 via-white to-white relative">
        <div className="fixed inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(245,158,11,0.05),transparent_70%)] pointer-events-none" />

        <div className="w-16 h-16 bg-white rounded-3xl flex items-center justify-center mb-6 border border-amber-100 shadow-xl backdrop-blur-xl relative z-10">
          <Sparkles className="w-8 h-8 text-amber-500 animate-pulse" />
        </div>
        <h2 className="text-xl font-bold text-zinc-900 mb-3 relative z-10">대화할 전문 챗봇을 선택해주세요</h2>
        <p className="text-sm text-zinc-500 max-w-sm mb-8 relative z-10">
          좌측 사이드바에서 기존 대화를 이어나가거나
          <br />홈 화면에서 새로운 챗봇을 선택하여 대화를 시작해보세요.
        </p>
        <Link href="/" passHref className="relative z-10">
          <Button className="bg-amber-500 hover:bg-amber-600 text-white font-semibold rounded-xl px-8 h-12 shadow-[0_0_15px_rgba(245,158,11,0.2)] transition-colors">
            챗봇 골라보기
          </Button>
        </Link>
      </div>
    );
  }

  // intent.kind === "session" — 실제 UI 는 ChatLayout 이 activeSessionId 로 렌더.
  return null;
}
