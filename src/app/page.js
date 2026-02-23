export default function Home() {
  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900">
      <main className="mx-auto flex w-full max-w-5xl flex-col gap-10 px-6 py-16 sm:px-10">
        <header className="flex flex-col gap-4">
          <p className="text-sm font-semibold uppercase tracking-widest text-zinc-500">
            NCPM · ERP Phase 1
          </p>
          <h1 className="text-4xl font-semibold leading-tight sm:text-5xl">
            고기류 중심 ERP 1단계 설계
          </h1>
          <p className="max-w-2xl text-lg leading-8 text-zinc-600">
            대기업 프랜차이즈 구조를 참고하되, 현재 1~2개 매장 규모에 맞춘
            안정형 구조입니다. 과설계를 피하고 고기류부터 단계적으로 확장합니다.
          </p>
        </header>

        <section className="grid gap-6 sm:grid-cols-2">
          <div className="rounded-2xl border border-zinc-200 bg-white p-6">
            <h2 className="text-xl font-semibold">현재 완료</h2>
            <ul className="mt-4 list-disc pl-5 text-zinc-700">
              <li>품목 마스터 구조 설계</li>
              <li>BOM 설계 시작 (1단계)</li>
              <li>고기류 발주 기준 설계</li>
            </ul>
          </div>
          <div className="rounded-2xl border border-zinc-200 bg-white p-6">
            <h2 className="text-xl font-semibold">확정 원칙</h2>
            <ul className="mt-4 list-disc pl-5 text-zinc-700">
              <li>FG 판매 시 RM/SF/CP 동시 차감</li>
              <li>반제품은 1단계 관리</li>
              <li>A형 발주 방식 적용</li>
            </ul>
          </div>
        </section>

        <section className="rounded-2xl border border-zinc-200 bg-white p-6">
          <h2 className="text-xl font-semibold">1순위 산출물</h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div className="rounded-xl bg-zinc-50 p-4">
              <p className="text-sm font-semibold text-zinc-500">DB 스키마</p>
              <p className="mt-2 text-zinc-700">
                Item Master · BOM · Inventory · Transaction
              </p>
            </div>
            <div className="rounded-xl bg-zinc-50 p-4">
              <p className="text-sm font-semibold text-zinc-500">핵심 로직</p>
              <p className="mt-2 text-zinc-700">
                판매 차감 → BOM 조회 → 재고 감소 → ROP 비교 → 발주 트리거
              </p>
            </div>
          </div>
        </section>

        <section className="rounded-2xl border border-zinc-200 bg-white p-6">
          <h2 className="text-xl font-semibold">다음 단계</h2>
          <ul className="mt-4 list-disc pl-5 text-zinc-700">
            <li>다점포 확장 구조</li>
            <li>반제품 2단계 BOM 전환</li>
            <li>OEM 연동 설계</li>
          </ul>
        </section>

        <footer className="flex flex-col gap-3 text-sm text-zinc-500">
          <p>문서 상세는 리포지토리의 `docs/erp-phase1.md`를 참고하세요.</p>
        </footer>
      </main>
    </div>
  );
}
