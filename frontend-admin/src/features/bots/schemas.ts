import { z } from "zod/v4";

export const clarificationPolicyOptionSchema = z.object({
  id: z.string(),
  label: z.string(),
});

export const clarificationRequiredSlotSchema = z.object({
  id: z.string(),
  label: z.string(),
  question: z.string(),
  selection_mode: z.enum(["single", "multiple"]),
  options: z.array(clarificationPolicyOptionSchema),
  allow_custom: z.boolean(),
});

export const clarificationPolicySchema = z.object({
  enabled: z.boolean(),
  rules: z.array(
    z.object({
      id: z.string(),
      name: z.string(),
      enabled: z.boolean(),
      priority: z.number(),
      request_examples: z.array(z.string()),
      why_ask: z.string(),
      document_refs: z.array(z.object({ document_id: z.string(), label: z.string() })),
      required_slots: z.array(clarificationRequiredSlotSchema),
      when_unknown: z.enum(["ask", "handoff", "allow_answer"]),
    })
  ),
});

// --- Bot 도메인 타입 ---
export type Bot = {
  id: string;
  name: string;
  description: string | null;
  tags: string[];
  is_active: boolean;
  system_prompt: string;
  llm_model: string;
  created_at: string;
  updated_at: string;
};

// --- LLM 모델 옵션 ---
export const LLM_MODEL_OPTIONS = [
  { label: "GPT-4o", value: "gpt-4o", provider: "openai" },
  { label: "GPT-4o Mini", value: "gpt-4o-mini", provider: "openai" },
  { label: "GPT-5", value: "gpt-5", provider: "openai" },
  { label: "Gemini 2.5 Flash", value: "gemini-2.5-flash", provider: "gemini" },
  {
    label: "Gemini 3.0 Flash",
    value: "gemini-3-flash-preview",
    provider: "gemini",
  },
  {
    label: "Gemini 3.1 Flash Lite",
    value: "gemini-3.1-flash-lite",
    provider: "gemini",
  },
  {
    label: "Gemini 3.5 Flash Lite",
    value: "gemini-3.5-flash-lite",
    provider: "gemini",
  },
] as const;

export type LLMProvider = "openai" | "gemini" | "unknown";

/** 모델명으로 Provider (OpenAI/Gemini) 판별 */
export function getModelProvider(modelName: string): LLMProvider {
  if (!modelName) return "unknown";
  const lower = modelName.toLowerCase();
  if (lower.startsWith("gpt")) return "openai";
  if (lower.startsWith("gemini")) return "gemini";
  return "unknown";
}

// --- Plan 타입 옵션 ---
export const PLAN_TYPE_OPTIONS = [
  { label: "무료 (Free)", value: "FREE" },
  { label: "프로 (Pro)", value: "PRO" },
] as const;

// --- 근거 조달 방식 ---
// 아래 9개 수치는 모두 같은 실행에서 나왔다 — 봇 11 · 45문항 전수(225셀).
// 커버리지·지연은 exports/wiki_eval/answers.json(kw_pct·elapsed_s),
// 지어냄율은 같은 답변을 규정 원문 250건에 대고 잰 audit_summary.json(fab_rate) 이다.
// (docs/architecture/handoff-evidence-audit-45set-2026-08-10.md)
//
// 재측정하면 RETRIEVAL_METRICS_SOURCE 와 아래 수치를 반드시 함께 바꾼다.
// 앞서 25문항 값이 45문항으로 갱신될 때 화면이 안 따라와 한동안 거짓을 표시했다.
export const RETRIEVAL_METRICS_SOURCE = "봇 11 · 45문항 · 2026-08-09 측정";

export const RETRIEVAL_MODE_OPTIONS = [
  {
    value: "file_search",
    label: "의미 검색 (file_search)",
    summary: "커버리지 56.6% · 7.3초 · 지어냄 14.2%",
    detail:
      "Gemini 가 스토어에서 직접 찾는다. 가장 많이 맞히지만 가장 많이 지어낸다.",
  },
  {
    value: "lexical",
    label: "어휘 검색 (규정 원문 주입)",
    summary: "커버리지 44.2% · 1.9초 · 지어냄 3.4%",
    detail:
      "BM25 로 규정 원문을 뽑아 그것만 준다. 덜 맞히고 덜 틀린다. 가장 빠르다.",
  },
  {
    value: "both",
    label: "둘 다",
    summary: "커버리지 50.1% · 5.8초 · 지어냄 11.4%",
    detail:
      "의미 검색에 규정 원문을 얹는다. 커버리지는 중간인데 원문과 어긋나는 답(모순)이 가장 많았다.",
  },
] as const;

export type RetrievalMode = (typeof RETRIEVAL_MODE_OPTIONS)[number]["value"];

// --- 답변 프리셋 ---
// 두 축(조달 방식 · 근거 검증)을 함께 바꾼다. 관리자가 축을 따로 이해하지 않아도
// 봇 성격만 고르면 되도록 한다. 축을 직접 건드리면 「사용자 지정」으로 표시된다.
export const ANSWER_PRESETS = [
  {
    key: "accuracy",
    label: "정확 우선",
    for: "정보 안내형 봇",
    retrieval_mode: "file_search",
    evidence_policy_mode: "legacy",
    note: "가장 많이 답한다. 대신 규정에 없는 말을 할 확률도 가장 높다.",
  },
  {
    key: "safety",
    label: "안전 우선",
    for: "상담·위기 봇 · 카카오 채널",
    retrieval_mode: "lexical",
    evidence_policy_mode: "strict",
    note: "지어냄이 약 1/4 로 줄고 응답이 4배 빠르다. 대신 답하지 못하는 질문이 늘어난다.",
  },
  {
    key: "balanced",
    label: "균형",
    for: "커버리지를 우선하되 속도도 필요한 봇",
    retrieval_mode: "both",
    evidence_policy_mode: "legacy",
    note: "커버리지는 중간인데 원문과 어긋나는 답이 가장 많다(6건 vs 정확 우선 3건) — 권장하지 않는다.",
  },
] as const;

export type AnswerPresetKey = (typeof ANSWER_PRESETS)[number]["key"];

/** 현재 두 축의 값에 해당하는 프리셋. 어디에도 맞지 않으면 null(= 사용자 지정). */
export function matchPreset(
  retrievalMode: string,
  evidencePolicyMode: string
): (typeof ANSWER_PRESETS)[number] | null {
  return (
    ANSWER_PRESETS.find(
      (p) =>
        p.retrieval_mode === retrievalMode &&
        p.evidence_policy_mode === evidencePolicyMode
    ) ?? null
  );
}

// --- 봇 생성 폼 Zod 스키마 ---
export const botFormSchema = z.object({
  name: z.string().min(2, { message: "봇 이름은 최소 2자 이상이어야 합니다." }),
  description: z.string(),
  tags: z.array(z.string()),
  is_active: z.boolean(),
  system_prompt: z
    .string()
    .min(1, { message: "시스템 프롬프트는 필수입니다." }),
  llm_model: z.string().min(1, { message: "LLM 모델을 선택해 주세요." }),
});

export type BotFormValues = z.infer<typeof botFormSchema>;

// --- 봇 수정 폼 Zod 스키마 (생성 폼 + 운영 메타데이터 필드 포함) ---
export const botEditFormSchema = z.object({
  name: z.string().min(2, { message: "봇 이름은 최소 2자 이상이어야 합니다." }),
  description: z.string(),
  tags: z.array(z.string()),
  is_active: z.boolean(),
  is_verified: z.boolean(),
  is_new: z.boolean(),
  plan_required: z.enum(["FREE", "PRO"]),
  system_prompt: z
    .string()
    .min(1, { message: "시스템 프롬프트는 필수입니다." }),
  llm_model: z.string().min(1, { message: "LLM 모델을 선택해 주세요." }),
  // 대화 기억 윈도우 — number Input의 value는 string이므로 coerce로 변환
  history_window: z.coerce
    .number()
    .int({ message: "정수를 입력해 주세요." })
    .min(0, { message: "0 이상이어야 합니다." }),
  evidence_policy_mode: z.enum(["legacy", "strict"]),
  retrieval_mode: z.enum(["file_search", "lexical", "both"]),
  clarify_enabled: z.boolean(),
  clarification_policy: clarificationPolicySchema,
});

export type BotEditFormValues = z.infer<typeof botEditFormSchema>;
