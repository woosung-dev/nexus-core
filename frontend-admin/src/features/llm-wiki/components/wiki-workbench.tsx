"use client"

// LLM 위키 작업대.
//
// 카파시 llm-wiki 패턴을 관리자 화면으로 옮긴 것.
// (https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
//
//   raw  — 규정집·용어집·공문·실측. 불변. 사람이 큐레이션한다.
//   wiki — LLM 이 쓴 상호연결 페이지. 사람은 읽고 판정만 한다.
//   lint — 모순·공백을 LLM 이 찾아 올린다. 사람이 정한다.
//
// 이 화면의 핵심 장치는 **문장 ↔ 원문 왕복**이다. 위키의 각 문장을 누르면 그 문장을
// 만든 raw 원문이 오른쪽에 그대로 열리고, 반대로 원문을 누르면 그 원문이 갱신한
// 위키 페이지들이 뜬다. 이게 없으면 "LLM 이 요약해준 글"에 그치고, 규정 도메인에서는
// 그 순간 못 쓰는 물건이 된다 — 근거를 못 되짚기 때문이다.
//
// 출처가 0건인 문장은 숨기지 않고 "근거 없음"으로 드러낸다. 공백은 지워야 할 흠이
// 아니라 관리자에게 물어야 할 목록이다.

import * as React from "react"
import {
  AlertTriangle,
  ArrowRight,
  CircleSlash,
  FileText,
  GitBranch,
  Link2,
  Radio,
  ScrollText,
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { cn } from "@/lib/utils"
import { CORPUS, SOURCES, type SourceKind } from "../sources"
import { CONFLICTS, GAPS, LOG, PAGES } from "../wiki"
import { findQuote } from "../highlight"

const SRC = new Map(SOURCES.map((s) => [s.id, s]))
const PAGE = new Map(PAGES.map((p) => [p.slug, p]))

/**
 * 형광펜이 칠해진 대목을 원문 상자 가운데로 끌어온다.
 *
 * 조문은 최대 3,500자다. 칠해 놓기만 하면 스크롤 밖에 있어 보이지 않는다.
 * `el.scrollIntoView()` 는 조상 스크롤러를 전부 움직여 페이지가 통째로 튀므로,
 * 상자 안에서만 움직이도록 scrollTop 을 직접 계산한다.
 * ref 콜백은 레이아웃이 잡히기 전에 돌아 scrollTop 이 먹지 않는다 — 그려진 뒤에 한다.
 */
function useScrollToMark(box: React.RefObject<HTMLElement | null>, dep: unknown) {
  React.useEffect(() => {
    const el = box.current
    const mark = el?.querySelector("mark")
    if (!el || !mark) return
    const id = requestAnimationFrame(() => {
      el.scrollTop +=
        mark.getBoundingClientRect().top - el.getBoundingClientRect().top - el.clientHeight / 2
    })
    return () => cancelAnimationFrame(id)
  }, [box, dep])
}

/** 산출물 파일을 새 탭에서 그대로 연다. 화면이 아니라 디스크의 파일을 보여 주기 위한 것이다. */
function FileLink({ file }: { file: string }) {
  return (
    <a
      href={`/api/wiki-file?path=${encodeURIComponent(file)}`}
      target="_blank"
      rel="noreferrer"
      title={file}
      className="inline-flex items-center gap-1 font-mono text-[10px] text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
    >
      <FileText className="size-3 shrink-0" />
      <span className="truncate">{file.replace("exports/wiki_2026-08/", "")}</span>
    </a>
  )
}

const KIND_STYLE: Record<SourceKind, string> = {
  reg: "bg-violet-100 text-violet-700 dark:bg-violet-950 dark:text-violet-300",
  glo: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  gm: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
  obs: "bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-300",
}
const KIND_LABEL: Record<SourceKind, string> = {
  reg: "규정집",
  glo: "용어집",
  gm: "공문",
  obs: "실측",
}

/** 어떤 페이지가 이 페이지를 가리키는가 — 역링크는 LLM 이 아니라 구조에서 나온다. */
function backlinks(slug: string) {
  return PAGES.filter((p) => p.links.includes(slug))
}

function SourceChip({
  id,
  active,
  onClick,
}: {
  id: string
  active?: boolean
  onClick?: () => void
}) {
  const s = SRC.get(id)
  if (!s) return null
  return (
    <button
      type="button"
      onClick={onClick}
      title={s.locator}
      className={cn(
        "inline-flex items-center gap-1 rounded-sm px-1.5 py-0.5 text-[10px] font-semibold align-middle",
        "transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-foreground",
        KIND_STYLE[s.kind],
        active && "ring-2 ring-foreground/40"
      )}
    >
      {KIND_LABEL[s.kind]} {s.locator.replace(/^(제|행정 |공문 )/, "").split("(")[0].trim().slice(0, 14)}
    </button>
  )
}

/* ── 컴파운딩 지표 — 이 위키가 자라고 있는가 ───────────────────── */
function Strip({ onJump }: { onJump: (t: string) => void }) {
  const links = PAGES.reduce((n, p) => n + p.links.length, 0)
  const anchored = PAGES.reduce((n, p) => n + p.claims.filter((c) => c.refs.length).length, 0)
  const total = PAGES.reduce((n, p) => n + p.claims.length, 0)

  const items = [
    { n: `${CORPUS.articles + CORPUS.glossary + CORPUS.gongmun}`, l: "raw 조각", s: `조문 ${CORPUS.articles} · 용어 ${CORPUS.glossary} · 공문 ${CORPUS.gongmun}` },
    { n: `${PAGES.length}`, l: "위키 페이지", s: `상호참조 ${links}건` },
    { n: `${anchored}/${total}`, l: "출처가 붙은 문장", s: "붙지 않은 문장은 근거 없음으로 표시" },
  ]
  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="flex flex-wrap items-start gap-x-10 gap-y-4">
        {items.map((it) => (
          <div key={it.l}>
            <p className="text-2xl font-bold tabular-nums leading-none">{it.n}</p>
            <p className="mt-1.5 text-xs font-medium">{it.l}</p>
            <p className="text-[11px] text-muted-foreground">{it.s}</p>
          </div>
        ))}
        <div className="ml-auto flex gap-2">
          <button
            onClick={() => onJump("conflicts")}
            className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-left transition-colors hover:bg-amber-100 dark:border-amber-900/50 dark:bg-amber-950/40 dark:hover:bg-amber-950/70"
          >
            <p className="text-xl font-bold tabular-nums leading-none text-amber-700 dark:text-amber-300">
              {CONFLICTS.length}
            </p>
            <p className="mt-1 text-[11px] font-medium text-amber-800 dark:text-amber-300">모순</p>
          </button>
          <button
            onClick={() => onJump("gaps")}
            className="rounded-md border px-3 py-2 text-left transition-colors hover:bg-accent"
          >
            <p className="text-xl font-bold tabular-nums leading-none">{GAPS.length}</p>
            <p className="mt-1 text-[11px] font-medium text-muted-foreground">문서 공백</p>
          </button>
        </div>
      </div>
    </div>
  )
}

/** 원문 패널 — 인용 구간에 형광펜을 칠하고, 그 자리로 스크롤하고, 실제 파일을 연다. */
function RawPanel({ focus }: { focus: { id: string; quote: string } | null }) {
  const box = React.useRef<HTMLParagraphElement>(null)
  useScrollToMark(box, focus)

  const s = focus ? SRC.get(focus.id) : undefined
  if (!s) {
    return <p className="text-xs text-muted-foreground">왼쪽 문장의 출처 표를 누르면 원문이 열립니다.</p>
  }
  const span = findQuote(s.quote, focus!.quote)
  return (
    <>
      <div className="mb-2 flex flex-wrap items-center gap-1.5">
        <Badge className={cn("text-[10px]", KIND_STYLE[s.kind])}>{s.doc}</Badge>
        <span className="font-mono text-[11px] text-muted-foreground">{s.locator}</span>
      </div>
      <p
        ref={box}
        className="max-h-72 overflow-auto whitespace-pre-wrap rounded bg-muted/50 p-2.5 text-[12px] leading-relaxed"
      >
        {span ? (
          <>
            {s.quote.slice(0, span[0])}
            <mark className="rounded-sm bg-yellow-200 px-0.5 text-foreground dark:bg-yellow-500/30">
              {s.quote.slice(span[0], span[1])}
            </mark>
            {s.quote.slice(span[1])}
          </>
        ) : (
          s.quote
        )}
      </p>
      <p className="mt-2 text-[10px] leading-relaxed text-muted-foreground">
        {span
          ? "요약이 아니라 원문입니다. 칠한 대목이 왼쪽 문장의 근거이며, 프로그램이 원문과 대조해 통과한 구간입니다."
          : "요약이 아니라 원문입니다. 이 문장에는 인용 구간이 딸려 있지 않습니다."}
      </p>
      <div className="mt-2 border-t pt-2">
        <FileLink file={s.file} />
      </div>
    </>
  )
}

/* ── 위키 열람 ───────────────────────────────────────────────── */
function WikiReader() {
  // PAGES 는 생성물이다. 레포에는 빈 껍데기만 커밋되므로 비어 있을 수 있다.
  const [slug, setSlug] = React.useState(PAGES[0]?.slug ?? "")
  // 열어 둔 원문 — 어느 소스인지(id)와 그 문장이 인용한 구간(quote)을 함께 들고 있어야
  // 조문 전문 안에서 근거 대목에 형광펜을 칠할 수 있다.
  const [focus, setFocus] = React.useState<{ id: string; quote: string } | null>(null)
  const page = PAGE.get(slug)

  // 페이지를 바꾸면 열어 둔 원문도 그 페이지의 첫 출처로 맞춘다.
  React.useEffect(() => {
    const first = page?.claims.find((c) => c.refs.length)
    setFocus(first ? { id: first.refs[0], quote: first.quote } : null)
  }, [slug]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!page) {
    return (
      <div className="rounded-lg border border-dashed bg-card p-10 text-center">
        <p className="text-sm font-medium">아직 위키가 없습니다.</p>
        <p className="mt-1.5 text-[13px] leading-relaxed text-muted-foreground">
          이 화면이 읽는 데이터는 생성물이라 레포에는 빈 껍데기만 들어 있습니다.
          <br />
          원본 문서로 ingest 를 돌린 뒤{" "}
          <code className="rounded bg-muted px-1.5 py-0.5 text-[12px]">
            exports/wiki_2026-08/_gen_admin.py --bot 11
          </code>{" "}
          을 실행하시면 채워집니다.
        </p>
      </div>
    )
  }

  const cats = Array.from(new Set(PAGES.map((p) => p.category)))
  const used = new Set(page.claims.flatMap((c) => c.refs))
  const back = backlinks(slug)

  return (
    <div className="grid gap-4 lg:grid-cols-[220px_minmax(0,1fr)_330px]">
      {/* 색인 — index.md 에 해당한다 */}
      <aside className="rounded-lg border bg-card p-3">
        <p className="mb-2 px-1 text-[11px] font-semibold text-muted-foreground">
          색인 · {PAGES.length}쪽
        </p>
        {cats.map((c) => (
          <div key={c} className="mb-3">
            <p className="mb-1 px-1 text-[10px] font-medium text-muted-foreground">{c}</p>
            {PAGES.filter((p) => p.category === c).map((p) => (
              <button
                key={p.slug}
                onClick={() => setSlug(p.slug)}
                className={cn(
                  "flex w-full items-center gap-1.5 rounded px-2 py-1.5 text-left text-[13px] transition-colors",
                  p.slug === slug ? "bg-accent font-semibold" : "hover:bg-accent/50"
                )}
              >
                <span className="truncate">{p.title}</span>
                {p.claims.some((cl) => cl.conflict) && (
                  <AlertTriangle className="ml-auto size-3 shrink-0 text-amber-600" />
                )}
              </button>
            ))}
          </div>
        ))}
      </aside>

      {/* 페이지 본문 — 문장마다 출처가 붙는다 */}
      <article className="min-w-0 rounded-lg border bg-card p-5">
        <div className="mb-1 flex flex-wrap items-center gap-2">
          <h2 className="text-lg font-semibold tracking-tight">{page.title}</h2>
          <Badge variant="secondary" className="text-[10px]">{page.category}</Badge>
          <span className="ml-auto text-[11px] text-muted-foreground">
            최근 갱신 · {page.updated}
          </span>
        </div>
        <div className="mb-3">
          <FileLink file={page.file} />
        </div>
        <p className="mb-4 text-sm leading-relaxed text-muted-foreground">{page.summary}</p>

        <div className="space-y-2.5">
          {page.claims.map((c, i) => {
            const conflict = c.conflict ? CONFLICTS.find((x) => x.id === c.conflict) : null
            const grounded = c.refs.length > 0
            return (
              <div
                key={i}
                className={cn(
                  "rounded-md border p-3",
                  !grounded && "border-dashed bg-muted/40",
                  conflict && "border-amber-300 bg-amber-50/60 dark:border-amber-900/50 dark:bg-amber-950/20"
                )}
              >
                <p className="text-[14px] leading-relaxed">{c.text}</p>
                <div className="mt-2 flex flex-wrap items-center gap-1.5">
                  {grounded ? (
                    c.refs.map((r) => (
                      <SourceChip
                        key={r}
                        id={r}
                        active={focus?.id === r && focus.quote === c.quote}
                        onClick={() => setFocus({ id: r, quote: c.quote })}
                      />
                    ))
                  ) : (
                    <span className="inline-flex items-center gap-1 text-[11px] font-medium text-muted-foreground">
                      <CircleSlash className="size-3" /> 근거 없음 — 관리자 확인 필요
                    </span>
                  )}
                  {conflict && (
                    <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-700 dark:text-amber-300">
                      <AlertTriangle className="size-3" /> {conflict.title.split(" — ")[0]}
                    </span>
                  )}
                </div>
              </div>
            )
          })}
        </div>

        {page.links.length > 0 && (
          <div className="mt-4 flex flex-wrap items-center gap-2 border-t pt-3">
            <span className="text-[11px] text-muted-foreground">이어지는 문서</span>
            {page.links.map((l) => (
              <Button
                key={l}
                variant="outline"
                size="sm"
                className="h-7 gap-1 text-xs"
                onClick={() => setSlug(l)}
              >
                <Link2 className="size-3" /> {PAGE.get(l)?.title ?? l}
              </Button>
            ))}
          </div>
        )}
      </article>

      {/* 컨텍스트 — 원문 · 역링크 */}
      <aside className="space-y-4">
        <div className="rounded-lg border bg-card p-4">
          <p className="mb-2 flex items-center gap-1.5 text-[11px] font-semibold">
            <FileText className="size-3.5" /> 원문 그대로
          </p>
          <RawPanel focus={focus} />
        </div>

        <div className="rounded-lg border bg-card p-4">
          <p className="mb-2 flex items-center gap-1.5 text-[11px] font-semibold">
            <Radio className="size-3.5" /> 이 페이지를 만든 원문 {used.size}건
          </p>
          <div className="flex flex-wrap gap-1.5">
            {Array.from(used).map((r) => (
              <SourceChip
                key={r}
                id={r}
                active={focus?.id === r}
                onClick={() => setFocus({ id: r, quote: "" })}
              />
            ))}
          </div>
        </div>

        <div className="rounded-lg border bg-card p-4">
          <p className="mb-2 flex items-center gap-1.5 text-[11px] font-semibold">
            <GitBranch className="size-3.5" /> 이 페이지를 가리키는 문서 {back.length}건
          </p>
          {back.length ? (
            <div className="flex flex-col gap-1">
              {back.map((p) => (
                <button
                  key={p.slug}
                  onClick={() => setSlug(p.slug)}
                  className="flex items-center gap-1.5 rounded px-1.5 py-1 text-left text-xs hover:bg-accent"
                >
                  <ArrowRight className="size-3 shrink-0 text-muted-foreground" />
                  {p.title}
                </button>
              ))}
            </div>
          ) : (
            <p className="text-xs text-muted-foreground">
              없습니다 — 고아 페이지입니다. 검사에서 잡아야 합니다.
            </p>
          )}
        </div>
      </aside>
    </div>
  )
}

/* ── 모순 — lint 산출물. 이 화면의 값어치는 여기 있다 ──────────── */
function Conflicts() {
  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">
        문서끼리, 또는 문서와 챗봇 실제 답변이 어긋난 자리입니다. 어느 쪽이 현행인지는
        문서만으로 정해지지 않아 <b className="text-foreground">관리자 판정</b>이 필요합니다.
      </p>
      {CONFLICTS.length === 0 && (
        <div className="rounded-lg border border-dashed bg-card p-8 text-center">
          <p className="text-sm font-medium">아직 어긋난 자리가 없습니다.</p>
          <p className="mt-1 text-[13px] text-muted-foreground">
            지금까지 읽은 {SOURCES.length}건 안에서는 서로 다른 말을 하는 대목이 나오지 않았습니다.
            자료를 더 넣으면 여기에 쌓입니다.
          </p>
        </div>
      )}
      {CONFLICTS.map((c) => (
        <div key={c.id} className="rounded-lg border-l-4 border-l-amber-500 bg-card p-4">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <AlertTriangle className="size-4 text-amber-600" />
            <span className="text-sm font-semibold">{c.title}</span>
            <Badge variant={c.status === "미해결" ? "destructive" : "secondary"} className="text-[10px]">
              {c.status}
            </Badge>
            <span className="ml-auto text-[11px] text-muted-foreground">
              {PAGE.get(c.page)?.title}
            </span>
          </div>

          {/* 3자 대립이면 "이쪽이 현행"이 어느 쪽인지 버튼 하나로는 못 가린다.
              선택을 각 진영 안에 둔다 — 관리자가 고르는 것은 문장이지 판정 종류가 아니다. */}
          <div className="mb-3 grid gap-2 md:grid-cols-3">
            {c.sides.map((s, i) => (
              <div key={i} className="flex flex-col rounded-md border bg-muted/40 p-2.5">
                <p className="mb-1 text-[11px] font-semibold text-muted-foreground">{s.label}</p>
                <p className="text-[13px] leading-relaxed">{s.says}</p>
                {s.ref && (
                  <div className="mt-1.5">
                    <SourceChip id={s.ref} />
                  </div>
                )}
                <Button size="sm" variant="outline" className="mt-2.5 h-7 w-full text-xs">
                  이것이 현행입니다
                </Button>
              </div>
            ))}
          </div>

          <p className="mb-3 text-[12px] text-muted-foreground">
            <b className="text-foreground">실측 —</b> {c.impact}
          </p>

          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[11px] text-muted-foreground">셋 다 아니라면</span>
            <Button size="sm" variant="outline" className="h-8">맞는 답을 직접 적겠습니다</Button>
            <Button size="sm" variant="ghost" className="h-8 text-muted-foreground">
              규정집에 넣어야 합니다
            </Button>
          </div>
        </div>
      ))}
    </div>
  )
}

/* ── 공백 — 문서가 답하지 못하는 자리 ─────────────────────────── */
function Gaps() {
  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">
        위키가 채우지 <b className="text-foreground">않은</b> 자리입니다. LLM 이 지어내면 출처 없는
        창작이 되므로, 비워 두고 관리자께 여쭙습니다.
      </p>
      {GAPS.length === 0 && (
        <div className="rounded-lg border border-dashed bg-card p-8 text-center">
          <p className="text-sm font-medium">여쭐 것이 없습니다.</p>
          <p className="mt-1 text-[13px] text-muted-foreground">
            지금까지 읽은 자료로 답이 되지 않는 자리가 나오지 않았습니다.
          </p>
        </div>
      )}
      {GAPS.map((g) => (
        <div key={g.id} className="rounded-lg border border-dashed bg-card p-4">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <CircleSlash className="size-4 text-muted-foreground" />
            <span className="text-sm font-semibold">{g.title}</span>
            <Badge variant="outline" className="font-mono text-[10px]">{g.hits}</Badge>
            <span className="ml-auto text-[11px] text-muted-foreground">{PAGE.get(g.page)?.title}</span>
          </div>
          <p className="mb-3 text-[13px] leading-relaxed text-muted-foreground">{g.detail}</p>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" className="h-8">답을 적어 주시면 위키에 넣습니다</Button>
            <Button size="sm" variant="outline" className="h-8">문서 신설이 필요합니다</Button>
          </div>
        </div>
      ))}
    </div>
  )
}

/* ── 기록 — log.md ───────────────────────────────────────────── */
function Log() {
  const OP: Record<string, { label: string; cls: string }> = {
    ingest: { label: "수집", cls: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300" },
    lint: { label: "검사", cls: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300" },
    query: { label: "질의", cls: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300" },
  }
  return (
    <div className="rounded-lg border bg-card">
      {LOG.map((l, i) => (
        <div key={i} className={cn("flex flex-wrap items-baseline gap-3 p-3", i > 0 && "border-t")}>
          <span className="font-mono text-[11px] text-muted-foreground">{l.date}</span>
          <Badge className={cn("text-[10px]", OP[l.op].cls)}>{OP[l.op].label}</Badge>
          <span className="text-[13px] font-medium">{l.title}</span>
          <span className="text-[12px] text-muted-foreground">{l.detail}</span>
        </div>
      ))}
    </div>
  )
}

export function WikiWorkbench() {
  const [tab, setTab] = React.useState("wiki")
  return (
    <Tabs value={tab} onValueChange={setTab} className="space-y-4">
      <Strip onJump={setTab} />
      <TabsList>
        <TabsTrigger value="wiki">
          <ScrollText className="size-3.5" /> 위키
        </TabsTrigger>
        <TabsTrigger value="conflicts">
          <AlertTriangle className="size-3.5" /> 모순 {CONFLICTS.length}
        </TabsTrigger>
        <TabsTrigger value="gaps">
          <CircleSlash className="size-3.5" /> 공백 {GAPS.length}
        </TabsTrigger>
        <TabsTrigger value="log">기록</TabsTrigger>
      </TabsList>
      <TabsContent value="wiki"><WikiReader /></TabsContent>
      <TabsContent value="conflicts"><Conflicts /></TabsContent>
      <TabsContent value="gaps"><Gaps /></TabsContent>
      <TabsContent value="log"><Log /></TabsContent>
    </Tabs>
  )
}
