export function HeroSection() {
  return (
    <section className="w-full py-12 md:py-24 lg:py-32 flex flex-col items-center justify-center text-center px-4">
      <div className="space-y-4 max-w-3xl">
        <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tighter text-foreground">
          식구님의 고민을 해결해줄 <br className="hidden sm:block" />
          <span className="text-amber-500">AI 챗봇</span>과 함께 찾아보세요
        </h1>
        <p className="mx-auto max-w-[700px] text-lg md:text-xl text-muted-foreground mt-4">
          다양한 AI 챗봇과 대화하며 궁금했던 부분을 해결하시면 좋겠습니다.
        </p>
      </div>
    </section>
  );
}
