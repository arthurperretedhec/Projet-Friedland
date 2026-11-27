import { HealthStatus } from "@/components/HealthStatus";
import { ScreeningApp } from "@/components/ScreeningApp";
import { APP_NAME } from "@/lib/site";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-20 border-b border-[var(--border)] bg-white">
        <div className="mx-auto flex max-w-[1440px] items-center gap-x-8 px-6 py-5 sm:px-10">
          <h1 className="flex items-center gap-3 text-[var(--heading)]">
            <span className="text-xl font-medium tracking-[0.18em] uppercase">Friedland</span>
            <span aria-hidden="true" className="h-6 w-px bg-[var(--accent)]" />
            <span className="text-sm font-light tracking-[0.12em] uppercase">Buyer Screening</span>
            <span className="sr-only"> · {APP_NAME}</span>
          </h1>
          <nav aria-label="Sections" className="hidden gap-6 sm:flex">
            <span aria-current="page" className="label-caps border-b-2 border-[var(--accent)] pb-1 !text-[var(--heading)]">
              New screening
            </span>
          </nav>
          <p className="label-caps ml-auto hidden !font-normal normal-case !tracking-normal text-[var(--muted)] md:block">
            112 management companies · 153 strategies · France
          </p>
        </div>
      </header>

      <main className="mx-auto w-full max-w-[1440px] flex-1 px-6 py-10 sm:px-10">
        <section className="mb-10 max-w-4xl">
          <p className="label-caps">Sell-side · financial buyers</p>
          <h2 className="display-light rule-blue mt-3 text-[clamp(2.25rem,5vw,4rem)]">Find the right financial partners</h2>
          <p className="mt-6 max-w-2xl text-base leading-relaxed">
            Describe the target: funds are filtered, scored and ranked. Pick the ones that go into the discussion
            materials and preview their banner.
          </p>
        </section>
        <ScreeningApp />
      </main>

      <footer className="bg-[var(--navy)] text-white">
        <div className="mx-auto flex max-w-[1440px] flex-wrap items-start justify-between gap-6 px-6 py-8 text-sm sm:px-10">
          <div>
            <p className="tracking-[0.18em] uppercase">Friedland</p>
            <p className="mt-1 text-white/70">EDHEC course project · public data, sources on every row</p>
          </div>
          <details className="text-xs text-white/70">
            <summary className="cursor-pointer">Technical diagnostics</summary>
            <div className="mt-2 max-w-md bg-white text-[var(--foreground)]">
              <HealthStatus />
            </div>
          </details>
        </div>
      </footer>
    </div>
  );
}
