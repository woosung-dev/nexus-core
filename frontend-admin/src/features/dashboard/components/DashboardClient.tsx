"use client"

import { useState } from "react"
import { useDashboardStats } from "../hooks"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Activity, Bot, MessageSquare, Users, AlertCircle, ThumbsUp } from "lucide-react"
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis, PieChart, Pie, Cell } from "recharts"

export function DashboardClient() {
  const [days, setDays] = useState("30")
  const { data, isLoading, isError } = useDashboardStats(Number(days))

  if (isLoading) {
    return <div className="p-8 text-center text-muted-foreground">대시보드 데이터를 불러오는 중입니다...</div>
  }

  if (isError || !data) {
    return <div className="p-8 text-center text-red-500">데이터를 불러오는데 실패했습니다.</div>
  }

  // 도넛 슬라이스 색상 — 상위 봇 구분용 팔레트 + '기타'용 회색.
  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#19A7CE', '#F76E11'];
  const ETC_COLOR = '#CBD5E1';
  const MAX_SLICES = 6;

  // 봇이 많아져도 도넛/범례가 깨지지 않도록 상위 N개 + '기타(N개)'로 묶는다.
  const sortedShares = [...data.bot_shares].sort((a, b) => b.count - a.count);
  const topShares = sortedShares.slice(0, MAX_SLICES);
  const restShares = sortedShares.slice(MAX_SLICES);
  const restTotal = restShares.reduce((sum, s) => sum + s.count, 0);
  const pieData =
    restTotal > 0
      ? [...topShares, { bot_name: `기타 (${restShares.length}개)`, count: restTotal }]
      : topShares;
  const shareTotal = pieData.reduce((sum, s) => sum + s.count, 0) || 1;
  const sliceColor = (entry: { bot_name: string }, i: number) =>
    entry.bot_name.startsWith("기타") ? ETC_COLOR : COLORS[i % COLORS.length];

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">대시보드</h1>
          <p className="text-muted-foreground">현재 시스템 모니터링 및 봇 사용 통계를 확인하세요.</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-muted-foreground">조회 기간:</span>
          <Select value={days} onValueChange={setDays}>
            <SelectTrigger className="w-[120px]">
              <SelectValue placeholder="기간 선택" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7">최근 7일</SelectItem>
              <SelectItem value="14">최근 14일</SelectItem>
              <SelectItem value="30">최근 30일</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">운영 중인 봇</CardTitle>
            <Bot className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data.stats.total_bots}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">등록된 총 사용자</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data.stats.total_users}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">금일 생성된 대화 수</CardTitle>
            <MessageSquare className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data.stats.today_chats}</div>
            <p className="text-xs text-muted-foreground">오늘 00:00 이후</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">오늘의 CS 긍정 점수</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data.stats.cs_score_today}%</div>
            <p className="text-xs text-muted-foreground">금일 피드백 누적 반영율</p>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        <Card className="col-span-4">
          <CardHeader>
            <CardTitle>최근 {days}일 대화 추이</CardTitle>
            <CardDescription>봇을 사용한 전체 대화량 변화입니다.</CardDescription>
          </CardHeader>
          <CardContent className="h-[350px] pb-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.recent_trends}>
                <XAxis dataKey="date" stroke="#888888" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(val) => val.slice(5)} />
                <YAxis stroke="#888888" fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip />
                <Bar dataKey="count" fill="currentColor" radius={[4, 4, 0, 0]} className="fill-primary" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="col-span-3">
          <CardHeader>
            <CardTitle>봇 점유율 (최근 {days}일)</CardTitle>
            <CardDescription>가장 많이 쓰인 봇의 비율입니다.</CardDescription>
          </CardHeader>
          <CardContent className="h-[350px] pb-4">
            {data.bot_shares.length > 0 ? (
              <div className="flex h-full flex-col">
                <div className="min-h-0 flex-1">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={pieData}
                        cx="50%"
                        cy="50%"
                        innerRadius={55}
                        outerRadius={80}
                        paddingAngle={3}
                        dataKey="count"
                        nameKey="bot_name"
                      >
                        {pieData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={sliceColor(entry, index)} />
                        ))}
                      </Pie>
                      <Tooltip
                        formatter={(value, name) => [
                          `${value}건 (${Math.round((Number(value) / shareTotal) * 100)}%)`,
                          name,
                        ]}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                {/* 커스텀 범례 — 봇 수와 무관하게 고정 크기, 이름 truncate + 비율 표기, 넘치면 스크롤 */}
                <ul className="mt-2 grid max-h-[104px] grid-cols-2 gap-x-3 gap-y-1 overflow-y-auto pr-1 text-xs">
                  {pieData.map((entry, index) => (
                    <li key={`legend-${index}`} className="flex min-w-0 items-center gap-1.5">
                      <span
                        className="h-2.5 w-2.5 shrink-0 rounded-full"
                        style={{ backgroundColor: sliceColor(entry, index) }}
                      />
                      <span className="truncate text-muted-foreground" title={entry.bot_name}>
                        {entry.bot_name}
                      </span>
                      <span className="ml-auto shrink-0 tabular-nums text-zinc-400">
                        {Math.round((entry.count / shareTotal) * 100)}%
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
                <div className="flex h-full items-center justify-center text-muted-foreground">데이터가 없습니다.</div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Feedbacks */}
      <Card>
        <CardHeader>
          <CardTitle>최근 접수된 사용자 피드백</CardTitle>
          <CardDescription>시스템 모니터링을 위해 접수된 긍정/부정 응답 대화 10건입니다.</CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="negative" className="w-full">
            <TabsList className="grid w-full grid-cols-2 mb-6">
              <TabsTrigger value="negative">부정적 피드백 ({data.neg_total})</TabsTrigger>
              <TabsTrigger value="positive">긍정적 피드백 ({data.pos_total})</TabsTrigger>
            </TabsList>
            
            <TabsContent value="negative">
              <div className="max-h-[500px] overflow-y-auto space-y-4 pr-2">
                {data.recent_negative_feedbacks.length === 0 ? (
                  <p className="text-sm text-muted-foreground py-10 text-center">최근 접수된 부정 피드백이 없습니다.</p>
                ) : (
                  <div className="space-y-4">
                    {data.recent_negative_feedbacks.map((f) => (
                      <div key={f.id} className="flex items-start gap-4 rounded-md border p-4 bg-card hover:bg-accent/50 transition-colors">
                        <AlertCircle className="mt-0.5 h-5 w-5 text-red-500 shrink-0" />
                        <div className="flex-1 space-y-1">
                          <p className="text-sm font-medium leading-none">
                            {f.session_title || "새 대화"} <span className="text-xs font-normal text-muted-foreground ml-2">({f.bot_name || "알 수 없는 봇"})</span>
                          </p>
                          <p className="text-sm text-muted-foreground line-clamp-3">
                            {f.content}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {new Date(f.created_at).toLocaleString('ko-KR')} | 사용자: {f.user_email || "알 수 없음"}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </TabsContent>

            <TabsContent value="positive">
              <div className="max-h-[500px] overflow-y-auto space-y-4 pr-2">
                {data.recent_positive_feedbacks.length === 0 ? (
                  <p className="text-sm text-muted-foreground py-10 text-center">최근 접수된 긍정 피드백이 없습니다.</p>
                ) : (
                  <div className="space-y-4">
                    {data.recent_positive_feedbacks.map((f) => (
                      <div key={f.id} className="flex items-start gap-4 rounded-md border p-4 bg-card hover:bg-accent/50 transition-colors">
                        <ThumbsUp className="mt-0.5 h-5 w-5 text-blue-500 shrink-0" />
                        <div className="flex-1 space-y-1">
                          <p className="text-sm font-medium leading-none">
                            {f.session_title || "새 대화"} <span className="text-xs font-normal text-muted-foreground ml-2">({f.bot_name || "알 수 없는 봇"})</span>
                          </p>
                          <p className="text-sm text-muted-foreground line-clamp-3">
                            {f.content}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {new Date(f.created_at).toLocaleString('ko-KR')} | 사용자: {f.user_email || "알 수 없음"}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  )
}
