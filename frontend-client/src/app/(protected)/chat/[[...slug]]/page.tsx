// 단일 catch-all chat 페이지 — Gemini 스타일 in-place URL 전환의 핵심.
// URL 패턴 3가지를 모두 받아 처리한다:
//   /chat            → 빈 상태 안내
//   /chat/{id}       → 기존 세션 (ChatLayout 이 URL 에서 직접 읽어 즉시 ChatArea 렌더)
//   /chat/new/{bot}  → POST /chats → 받은 id 로 history.replaceState (route navigation 없음)
//
// sessionId 의 단일 진실원은 ChatLayout 안의 useParams. 본 페이지는 new flow 의 짧은 윈도우를
// store(useChatStore.newFlowSession) 에 기록해 history.replaceState 직후의 race 만 메꾼다.
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
  const beginNewFlow = useChatStore((s) => s.beginNewFlow);
  const completeNewFlow = useChatStore((s) => s.completeNewFlow);
  const clearNewFlow = useChatStore((s) => s.clearNewFlow);

  // StrictMode 의 effect 중복 실행으로 세션이 두 번 생성되지 않도록 가드.
  // 값이 같은 botId 일 때만 skip — 봇이 바뀌면 새로 시작해야 함.
  const creatingForBotRef = useRef<string | null>(null);

  const intent = parseIntent(params?.slug);

  useEffect(() => {
    // session / empty 흐름에서는 store 의 new flow 잔존 데이터를 정리한다 (다음 새 봇 클릭 시 stale 방지).
    if (intent.kind === "session" || intent.kind === "empty") {
      creatingForBotRef.current = null;
      clearNewFlow();
      return;
    }

    // intent.kind === "new"
    if (creatingForBotRef.current === intent.botId) return;
    creatingForBotRef.current = intent.botId;

    // 동기적으로 store 에 "이 봇으로 진행 중" 상태 기록 → 이전 봇의 잔존 값이 한 프레임도 새지 않음.
    beginNewFlow(intent.botId);

    api
      .post<ChatSessionResponse>(`/chats?bot_id=${intent.botId}`)
      .then((res) => {
        // Race 방어: 응답을 기다리는 동안 사용자가 다른 봇으로 빠르게 이동했다면,
        // 이 응답은 더 이상 현재 화면과 관계 없음 → URL/store 어느 것도 건드리지 않는다.
        if (creatingForBotRef.current !== intent.botId) return;

        const created = res.data;

        // 사이드바 캐시 prepend — idempotent precreate 가 같은 세션 반환 시 dedupe.
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

        // ★ 핵심: history.replaceState 로 URL 만 변경 — Next.js 의 라우트 mount 는 그대로.
        // 첫 인자에 빈 {} 를 넘기면 Next.js App Router 가 window.history.state 에 보관하는
        // 내부 라우트 트리(__NA, tree 등)가 날아가서 뒤로가기 시 풀 리로드가 발생함.
        // 반드시 기존 state 를 유지한 채 URL 만 갱신해야 한다.
        window.history.replaceState(
          window.history.state,
          "",
          `/chat/${created.id}`,
        );
        completeNewFlow(intent.botId, String(created.id));
      })
      .catch((err) => {
        console.error("Failed to create chat session:", err);
        // 응답이 늦게 도착해 이미 다른 봇 흐름이 진행 중이면 store 를 건드리지 않는다.
        if (creatingForBotRef.current === intent.botId) {
          creatingForBotRef.current = null;
          clearNewFlow();
          router.replace("/");
        }
      });
  // params 변화에 반응 (사이드바 클릭 등). history.replaceState 는 params 갱신하지 않으므로 안전.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params?.slug?.join("/")]);

  // 주의: 별도 unmount cleanup 으로 clearNewFlow 를 호출하면 React StrictMode 의
  // 의도적 더블 마운트가 발생할 때 첫 마운트의 beginNewFlow → cleanup 의 clearNewFlow →
  // 두 번째 마운트에선 creatingForBotRef 가드로 beginNewFlow 가 skip 됨 → 결과적으로
  // POST 응답이 도착해도 newFlowSession 이 null 이라 completeNewFlow 가 무시되는 race 발생.
  // store 는 (a) intent 가 session/empty 일 때 동일 useEffect 안에서, (b) 다른 봇으로 새 new flow
  // 가 시작될 때 beginNewFlow 가 덮어쓰는 식으로 자연 정리되므로 별도 unmount cleanup 불필요.

  // ChatLayout 의 children 으로 전달 — activeSessionId 가 비어있을 때만 표시된다.
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

  // intent.kind === "session" — 실제 UI 는 ChatLayout 이 URL 의 useParams 로 직접 그려줌.
  return null;
}
