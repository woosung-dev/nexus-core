import { MessageCircle, Bot, Clock } from "lucide-react";

export function ActivityStatsSection() {
  const stats = [
    { label: "총 대화", value: "127", icon: <MessageCircle className="w-5 h-5 text-amber-500" /> },
    { label: "사용한 챗봇", value: "8", icon: <Bot className="w-5 h-5 text-amber-500" /> },
    { label: "총 사용 시간", value: "24h", icon: <Clock className="w-5 h-5 text-amber-500" /> },
  ];

  return (
    <section className="bg-zinc-950/80 border border-zinc-800 rounded-xl p-8 backdrop-blur-xl">
      <h2 className="text-xl font-bold text-white mb-8">활동 통계</h2>
      
      <div className="grid grid-cols-3 gap-6">
        {stats.map((stat, i) => (
          <div key={i} className="flex flex-col items-center">
            <div className="w-16 h-16 rounded-full flex items-center justify-center bg-amber-500/10 mb-4 ring-1 ring-amber-500/20">
              {stat.icon}
            </div>
            <p className="text-2xl font-bold text-white mb-1">{stat.value}</p>
            <p className="text-sm text-zinc-400 text-center">{stat.label}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
