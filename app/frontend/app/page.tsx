import { HealthStatus } from "@/components/HealthStatus";
import { ScreeningApp } from "@/components/ScreeningApp";
import { APP_NAME } from "@/lib/site";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-[var(--header-2)] bg-[var(--header)]">
        <div className="mx-auto flex max-w-[1600px] flex-wrap items-center gap-x-6 gap-y-1 px-4 py-3 sm:px-6">
          <h1 className="flex items-baseline gap-2 text-base font-semibold tracking-tight">
            <span className="rounded-sm bg-[var(--accent)] px-1.5 py-0.5 text-xs font-bold tracking-widest text-white">FBS</span>
            {APP_NAME}
          </h1>
          <nav aria-label="Sections" className="flex gap-4 text-sm">
            <span aria-current="page" className="border-b-2 border-[var(--accent)] pb-0.5 font-medium">
              Screening acquéreurs
            </span>
          </nav>
          <p className="ml-auto text-xs text-[var(--muted)]">Base : 112 sociétés de gestion · 153 stratégies · France</p>
        </div>
      </header>
      <main className="mx-auto w-full max-w-[1600px] flex-1 px-4 py-6 sm:px-6">
        <p className="mb-5 max-w-3xl text-sm text-[var(--muted)]">
          Identifier les fonds de private equity susceptibles d&apos;investir dans une société, les classer, choisir ceux qui iront
          dans les discussion materials et prévisualiser leur bandeau.
        </p>
        <ScreeningApp />
      </main>
      <footer className="mx-auto w-full max-w-[1600px] px-4 pb-6 sm:px-6">
        <details className="text-xs text-[var(--muted)]">
          <summary className="cursor-pointer">Diagnostic technique</summary>
          <div className="mt-2 max-w-md">
            <HealthStatus />
          </div>
        </details>
      </footer>
    </div>
  );
}
