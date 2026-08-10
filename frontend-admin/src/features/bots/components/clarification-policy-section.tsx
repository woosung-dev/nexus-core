"use client"

import * as React from "react"
import { useQuery } from "@tanstack/react-query"
import { AlertTriangle, Copy, GripVertical, Plus, Trash2 } from "lucide-react"

import { documentKeys, fetchDocuments } from "@/features/documents/api"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea"
import type {
  ClarificationPolicy,
  ClarificationPolicyDocumentRef,
  ClarificationPolicyRule,
  ClarificationPolicyTestResponse,
  ClarificationRequiredSlot,
} from "../types"
import { testClarificationPolicy } from "../api"

type PolicySectionProps = {
  botId: number
  initialPolicy: ClarificationPolicy
  onPersist: (policy: ClarificationPolicy) => Promise<void>
}

const steps = ["적용 요청", "필수 확인 항목", "근거 문서", "검토·저장"]

function makeId(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
}

function emptySlot(): ClarificationRequiredSlot {
  return {
    id: makeId("slot"),
    label: "",
    question: "",
    selection_mode: "single",
    options: [
      { id: makeId("option"), label: "" },
      { id: makeId("option"), label: "" },
    ],
    allow_custom: true,
  }
}

function emptyRule(): ClarificationPolicyRule {
  return {
    id: makeId("rule"),
    name: "",
    enabled: false,
    priority: 0,
    request_examples: ["", ""],
    why_ask: "",
    document_refs: [],
    required_slots: [],
    when_unknown: "ask",
  }
}

function cloneDraft(rule: ClarificationPolicyRule): ClarificationPolicyRule {
  return {
    ...rule,
    id: makeId("rule"),
    name: rule.name ? `${rule.name} 복사본` : "복사본",
    enabled: false,
    document_refs: rule.document_refs.map((document) => ({ ...document })),
    request_examples: [...rule.request_examples],
    required_slots: rule.required_slots.map((slot) => ({
      ...slot,
      id: makeId("slot"),
      options: slot.options.map((option) => ({ ...option, id: makeId("option") })),
    })),
  }
}

function moveItem<T>(items: T[], from: number, to: number): T[] {
  const next = [...items]
  const [item] = next.splice(from, 1)
  next.splice(to, 0, item)
  return next
}

function activationError(rule: ClarificationPolicyRule, documentCount: number): string | null {
  if (!rule.name.trim()) return "규칙 이름을 입력해 주세요."
  if (rule.request_examples.filter((example) => example.trim()).length < 2) {
    return "사용자 요청 예시를 2개 이상 입력해 주세요."
  }
  if (rule.request_examples.filter((example) => example.trim()).length > 5) {
    return "사용자 요청 예시는 최대 5개까지 등록할 수 있습니다."
  }
  if (!rule.why_ask.trim()) return "질문이 필요한 이유를 입력해 주세요."
  if (documentCount === 0) return "근거 문서를 먼저 연결해 주세요."
  if (rule.document_refs.length === 0) return "근거 문서를 1개 이상 선택해 주세요."
  if (rule.required_slots.length < 1 || rule.required_slots.length > 3) {
    return "필수 확인 항목을 1~3개 등록해 주세요."
  }
  for (const slot of rule.required_slots) {
    if (!slot.label.trim() || !slot.question.trim()) {
      return "필수 확인 항목의 이름과 질문을 입력해 주세요."
    }
    if (slot.options.length < 2 || slot.options.length > 5) {
      return "각 항목에는 선택지를 2~5개 등록해 주세요."
    }
    if (slot.options.some((option) => !option.label.trim())) {
      return "선택지 문구를 모두 입력해 주세요."
    }
  }
  return null
}

function RuleEditor({
  rule,
  step,
  documents,
  onChange,
}: {
  rule: ClarificationPolicyRule
  step: number
  documents: { file_id: string; display_name: string }[]
  onChange: (rule: ClarificationPolicyRule) => void
}) {
  const [draggedSlotIndex, setDraggedSlotIndex] = React.useState<number | null>(null)

  const updateSlot = (index: number, slot: ClarificationRequiredSlot) => {
    const requiredSlots = [...rule.required_slots]
    requiredSlots[index] = slot
    onChange({ ...rule, required_slots: requiredSlots })
  }

  const toggleDocument = (document: { file_id: string; display_name: string }) => {
    const exists = rule.document_refs.some((item) => item.document_id === document.file_id)
    const documentRefs: ClarificationPolicyDocumentRef[] = exists
      ? rule.document_refs.filter((item) => item.document_id !== document.file_id)
      : [...rule.document_refs, { document_id: document.file_id, label: document.display_name }]
    onChange({ ...rule, document_refs: documentRefs })
  }

  if (step === 0) {
    return (
      <div className="space-y-4">
        <label className="block text-sm font-medium">
          규칙 이름
          <Input className="mt-2" value={rule.name} onChange={(event) => onChange({ ...rule, name: event.target.value })} />
        </label>
        <label className="block text-sm font-medium">
          우선순위
          <Input type="number" className="mt-2" value={rule.priority} onChange={(event) => onChange({ ...rule, priority: Number(event.target.value) || 0 })} />
        </label>
        <div className="space-y-2">
          <p className="text-sm font-medium">사용자 요청 예시</p>
          {rule.request_examples.map((example, index) => (
            <div className="flex gap-2" key={`${rule.id}-example-${index}`}>
              <Input
                value={example}
                placeholder="예: 환불 가능한가요?"
                onChange={(event) => {
                  const requestExamples = [...rule.request_examples]
                  requestExamples[index] = event.target.value
                  onChange({ ...rule, request_examples: requestExamples })
                }}
              />
              <Button
                type="button"
                variant="ghost"
                size="icon"
                aria-label="요청 예시 삭제"
                disabled={rule.request_examples.length <= 2}
                onClick={() => onChange({ ...rule, request_examples: rule.request_examples.filter((_, itemIndex) => itemIndex !== index) })}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          ))}
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={rule.request_examples.length >= 5}
            onClick={() => onChange({ ...rule, request_examples: [...rule.request_examples, ""] })}
          >
            <Plus className="mr-1 h-4 w-4" /> 예시 추가
          </Button>
        </div>
        <label className="block text-sm font-medium">
          바로 답변하면 안 되는 이유
          <Textarea className="mt-2" value={rule.why_ask} onChange={(event) => onChange({ ...rule, why_ask: event.target.value })} />
        </label>
      </div>
    )
  }

  if (step === 1) {
    return (
      <div className="space-y-4">
        <p className="text-sm text-muted-foreground">질문 순서는 드래그해서 바꿀 수 있습니다. 최대 3개까지 등록합니다.</p>
        {rule.required_slots.map((slot, index) => (
          <div
            className="rounded-lg border p-4"
            draggable
            key={slot.id}
            onDragStart={() => setDraggedSlotIndex(index)}
            onDragOver={(event) => event.preventDefault()}
            onDrop={() => {
              if (draggedSlotIndex === null || draggedSlotIndex === index) return
              onChange({ ...rule, required_slots: moveItem(rule.required_slots, draggedSlotIndex, index) })
              setDraggedSlotIndex(null)
            }}
          >
            <div className="mb-3 flex items-center justify-between">
              <p className="flex items-center gap-2 text-sm font-medium"><GripVertical className="h-4 w-4 text-muted-foreground" /> 필수 항목 {index + 1}</p>
              <Button type="button" variant="ghost" size="sm" onClick={() => onChange({ ...rule, required_slots: rule.required_slots.filter((_, itemIndex) => itemIndex !== index) })}>삭제</Button>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="text-sm">항목 이름<Input className="mt-1" value={slot.label} onChange={(event) => updateSlot(index, { ...slot, label: event.target.value })} /></label>
              <label className="text-sm">선택 방식
                <select className="mt-1 flex h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm" value={slot.selection_mode} onChange={(event) => updateSlot(index, { ...slot, selection_mode: event.target.value as ClarificationRequiredSlot["selection_mode"] })}>
                  <option value="single">하나 선택</option><option value="multiple">복수 선택</option>
                </select>
              </label>
            </div>
            <label className="mt-3 block text-sm">사용자에게 보여 줄 질문<Input className="mt-1" value={slot.question} onChange={(event) => updateSlot(index, { ...slot, question: event.target.value })} /></label>
            <div className="mt-3 space-y-2"><p className="text-sm">선택지</p>
              {slot.options.map((option, optionIndex) => (
                <div className="flex gap-2" key={option.id}>
                  <Input value={option.label} placeholder="선택지 문구" onChange={(event) => {
                    const options = [...slot.options]
                    options[optionIndex] = { ...option, label: event.target.value }
                    updateSlot(index, { ...slot, options })
                  }} />
                  <Button type="button" variant="ghost" size="icon" disabled={slot.options.length <= 2} aria-label="선택지 삭제" onClick={() => updateSlot(index, { ...slot, options: slot.options.filter((_, itemIndex) => itemIndex !== optionIndex) })}><Trash2 className="h-4 w-4" /></Button>
                </div>
              ))}
              <Button type="button" variant="outline" size="sm" disabled={slot.options.length >= 5} onClick={() => updateSlot(index, { ...slot, options: [...slot.options, { id: makeId("option"), label: "" }] })}><Plus className="mr-1 h-4 w-4" />선택지 추가</Button>
            </div>
            <label className="mt-3 flex items-center gap-2 text-sm"><Switch checked={slot.allow_custom} onCheckedChange={(allowCustom) => updateSlot(index, { ...slot, allow_custom: allowCustom })} /> 직접 입력 허용</label>
          </div>
        ))}
        <Button type="button" variant="outline" disabled={rule.required_slots.length >= 3} onClick={() => onChange({ ...rule, required_slots: [...rule.required_slots, emptySlot()] })}><Plus className="mr-1 h-4 w-4" />필수 항목 추가</Button>
      </div>
    )
  }

  if (step === 2) {
    return (
      <div className="space-y-3">
        {documents.length === 0 ? <p className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">근거 문서를 먼저 연결해 주세요.</p> : documents.map((document) => {
          const checked = rule.document_refs.some((item) => item.document_id === document.file_id)
          return <label className="flex cursor-pointer items-center gap-3 rounded-lg border p-3 text-sm" key={document.file_id}><input type="checkbox" checked={checked} onChange={() => toggleDocument(document)} /><span>{document.display_name}</span></label>
        })}
        {rule.document_refs.map((document, index) => <label className="block text-sm" key={document.document_id}>근거 메모 (선택)<Input className="mt-1" value={document.label} onChange={(event) => {
          const documentRefs = [...rule.document_refs]
          documentRefs[index] = { ...document, label: event.target.value }
          onChange({ ...rule, document_refs: documentRefs })
        }} /></label>)}
      </div>
    )
  }

  return (
    <div className="space-y-4 rounded-lg border bg-muted/30 p-4 text-sm">
      <p><span className="font-medium">{rule.name || "이름 없는 규칙"}</span> 요청에서는 아래 항목을 먼저 확인합니다.</p>
      <ul className="list-disc space-y-1 pl-5">{rule.required_slots.map((slot) => <li key={slot.id}>{slot.question || "질문 미입력"}</li>)}</ul>
      <label className="block">판단이 애매할 때
        <select className="mt-1 flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm" value={rule.when_unknown} onChange={(event) => onChange({ ...rule, when_unknown: event.target.value as ClarificationPolicyRule["when_unknown"] })}>
          <option value="ask">추가 확인 질문 표시</option><option value="handoff">담당자 안내</option><option value="allow_answer">일반 설명 계속</option>
        </select>
      </label>
    </div>
  )
}

export function ClarificationPolicySection({ botId, initialPolicy, onPersist }: PolicySectionProps) {
  const [policy, setPolicy] = React.useState<ClarificationPolicy>(initialPolicy)
  const [editing, setEditing] = React.useState<ClarificationPolicyRule | null>(null)
  const [step, setStep] = React.useState(0)
  const [saving, setSaving] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)
  const [testMessage, setTestMessage] = React.useState("")
  const [testResult, setTestResult] = React.useState<ClarificationPolicyTestResponse | null>(null)
  const [testing, setTesting] = React.useState(false)
  const { data: documentList } = useQuery({
    queryKey: documentKeys.byBot(botId),
    queryFn: () => fetchDocuments(botId),
  })
  const documents = documentList?.documents ?? []

  const persist = async (nextPolicy: ClarificationPolicy) => {
    setSaving(true)
    setError(null)
    try {
      await onPersist(nextPolicy)
      setPolicy(nextPolicy)
      setEditing(null)
      setStep(0)
    } catch {
      setError("저장하지 못했습니다. 활성 규칙의 필수 항목과 근거 문서를 다시 확인해 주세요.")
    } finally {
      setSaving(false)
    }
  }

  const saveDraft = () => {
    if (!editing) return
    const rule = { ...editing, enabled: false }
    const rules = policy.rules.some((item) => item.id === rule.id)
      ? policy.rules.map((item) => item.id === rule.id ? rule : item)
      : [...policy.rules, rule]
    void persist({ ...policy, rules })
  }

  const startRule = () => {
    if (!editing) return
    const validationMessage = activationError(editing, documents.length)
    if (validationMessage) {
      setError(validationMessage)
      return
    }
    const rule = { ...editing, enabled: true, request_examples: editing.request_examples.map((example) => example.trim()) }
    const rules = policy.rules.some((item) => item.id === rule.id)
      ? policy.rules.map((item) => item.id === rule.id ? rule : item)
      : [...policy.rules, rule]
    void persist({ enabled: true, rules })
  }

  const togglePolicy = (enabled: boolean) => {
    if (!enabled) {
      void persist({ ...policy, enabled: false })
      return
    }
    const invalidRule = policy.rules.find((rule) => rule.enabled && activationError(rule, documents.length))
    if (invalidRule) {
      setError(`“${invalidRule.name || "이름 없는 규칙"}”을(를) 먼저 완성해 주세요.`)
      return
    }
    void persist({ ...policy, enabled: true })
  }

  const runTest = async () => {
    const message = testMessage.trim()
    if (!message) {
      setError("테스트할 사용자 요청을 입력해 주세요.")
      return
    }
    setTesting(true)
    setError(null)
    try {
      setTestResult(await testClarificationPolicy(botId, policy, message))
    } catch {
      setError("테스트 결과를 가져오지 못했습니다. 활성 규칙과 근거 문서를 확인해 주세요.")
      setTestResult(null)
    } finally {
      setTesting(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center gap-2">
          <CardTitle>추가 확인 질문 정책</CardTitle>
          <Badge variant="outline" className="text-[10px] font-normal">미리보기 전용</Badge>
        </div>
        <CardDescription>상황에 따라 안내가 달라지는 요청에서, 답변 전에 꼭 확인할 항목을 정합니다.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="flex items-center justify-between gap-4 rounded-lg border p-4">
          <div><p className="font-medium">필수 확인 질문 사용</p><p className="mt-1 text-sm text-muted-foreground">활성 규칙에서 누락된 항목은 먼저 질문합니다.</p></div>
          <Switch checked={policy.enabled} disabled={saving} onCheckedChange={togglePolicy} />
        </div>
        {/* 규칙은 저장되지만 런타임이 안 읽는다 — 실제 대화에 쓰이는 곳이 없다. */}
        <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 p-2 dark:border-amber-900/40 dark:bg-amber-950/30">
          <AlertTriangle className="mt-0.5 size-3.5 shrink-0 text-amber-600 dark:text-amber-400" />
          <p className="text-[11px] leading-relaxed text-foreground/90">
            규칙은 저장되지만 <b>실제 사용자 대화에는 아직 적용되지 않습니다.</b>{" "}
            지금은 아래 「테스트하기」에서만 결과를 확인할 수 있습니다.
          </p>
        </div>
        {error && <p role="alert" className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">{error}</p>}

        {editing ? (
          <section className="space-y-5 rounded-lg border p-4">
            <div className="flex flex-wrap gap-2">{steps.map((label, index) => <Button type="button" size="sm" key={label} variant={step === index ? "default" : "outline"} onClick={() => setStep(index)}>{index + 1}. {label}</Button>)}</div>
            <RuleEditor rule={editing} step={step} documents={documents} onChange={setEditing} />
            <div className="flex flex-wrap justify-between gap-2 border-t pt-4">
              <div className="flex gap-2"><Button type="button" variant="outline" disabled={step === 0} onClick={() => setStep((current) => current - 1)}>이전</Button><Button type="button" variant="outline" disabled={step === steps.length - 1} onClick={() => setStep((current) => current + 1)}>다음</Button></div>
              <div className="flex gap-2"><Button type="button" variant="outline" disabled={saving} onClick={saveDraft}>초안 저장</Button><Button type="button" disabled={saving} onClick={startRule}>사용 시작</Button></div>
            </div>
          </section>
        ) : (
          <>
            <div className="space-y-3">
              {policy.rules.map((rule) => <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border p-4" key={rule.id}><div><p className="font-medium">{rule.name || "이름 없는 초안"}</p><p className="mt-1 text-sm text-muted-foreground">{rule.enabled ? "사용 중" : "초안"} · 요청 예시 {rule.request_examples.filter((item) => item.trim()).length}개 · 필수 확인 {rule.required_slots.length}개 · 근거 문서 {rule.document_refs.length}개</p></div><div className="flex gap-2"><Button type="button" variant="outline" size="sm" onClick={() => { setEditing(rule); setStep(0) }}>편집</Button><Button type="button" variant="outline" size="sm" onClick={() => { setEditing(cloneDraft(rule)); setStep(0) }}><Copy className="mr-1 h-4 w-4" />복제</Button>{rule.enabled && <Button type="button" variant="outline" size="sm" disabled={saving} onClick={() => void persist({ ...policy, rules: policy.rules.map((item) => item.id === rule.id ? { ...item, enabled: false } : item) })}>비활성화</Button>}</div></div>)}
              {policy.rules.length === 0 && <p className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">등록된 규칙이 없습니다.</p>}
            </div>
            <Button type="button" variant="outline" onClick={() => { setEditing(emptyRule()); setStep(0); setError(null) }}><Plus className="mr-1 h-4 w-4" />새 규칙 만들기</Button>
          </>
        )}

        <section className="space-y-3 rounded-lg border bg-muted/20 p-4">
          <div><p className="font-medium">테스트하기</p><p className="mt-1 text-sm text-muted-foreground">현재 화면의 정책으로 이 요청에 어떤 확인 질문이 나오는지 미리 봅니다.</p></div>
          <Textarea value={testMessage} onChange={(event) => setTestMessage(event.target.value)} placeholder="예: 국제 축복 준비에 필요한 서류를 알려 주세요." />
          <Button type="button" variant="outline" disabled={testing} onClick={() => void runTest()}>{testing ? "확인 중..." : "테스트하기"}</Button>
          {testResult && <div className="space-y-2 rounded-md border bg-background p-3 text-sm"><p className="font-medium">{testResult.message}</p>{testResult.applied_rule_name && <p>적용 규칙: {testResult.applied_rule_name}</p>}{testResult.questions.length > 0 && <ul className="list-disc space-y-1 pl-5">{testResult.questions.map((slot) => <li key={slot.id}>{slot.question}</li>)}</ul>}{testResult.document_refs.length > 0 && <p className="text-muted-foreground">근거: {testResult.document_refs.map((document) => document.label).join(", ")}</p>}</div>}
        </section>
      </CardContent>
    </Card>
  )
}
