import { BotCard, BotData } from "./BotCard";

interface BotGridProps {
  bots: BotData[];
  title?: string;
}

export function BotGrid({ bots, title }: BotGridProps) {
  if (!bots || bots.length === 0) {
    return (
      <div className="w-full py-12 flex flex-col items-center justify-center text-zinc-500 space-y-4">
        <p>조건에 맞는 AI 챗봇이 없습니다.</p>
      </div>
    );
  }

  return (
    <div className="w-full px-4 mb-20">
      {title && (
        <h2 className="text-2xl font-bold mb-6 text-foreground">{title}</h2>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {bots.map((bot) => (
          <BotCard key={bot.id} bot={bot} />
        ))}
      </div>
    </div>
  );
}
