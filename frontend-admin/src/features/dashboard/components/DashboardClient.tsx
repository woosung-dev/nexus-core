"use client"

import { useState } from "react"
import { useDashboardStats } from "../hooks"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Activity, Bot, MessageSquare, Users, AlertCircle, ThumbsUp } from "lucide-react"
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis, PieChart, Pie, Cell, Legend } from "recharts"

export function DashboardClient() {
  const [days, setDays] = useState("30")
  const { data, isLoading, isError } = useDashboardStats(Number(days))

  if (isLoading) {
    return <div className="p-8 text-center text-muted-foreground">대시보드 데이터를 불러오는 중입니다...</div>
  }

  if (isError || !data) {
    return <div className="p-8 text-center text-red-500">데이터를 불러오는데 실패했습니다.</div>
  }

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'];

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
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={data.bot_shares}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="count"
                    nameKey="bot_name"
                  >
                    {data.bot_shares.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend verticalAlign="bottom" height={36} />
                </PieChart>
              </ResponsiveContainer>
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
