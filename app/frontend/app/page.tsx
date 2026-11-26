import { HealthStatus } from "@/components/HealthStatus";
import { ScreeningApp } from "@/components/ScreeningApp";
import { APP_NAME } from "@/lib/site";

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-7xl flex-col gap-6 px-4 py-8 sm:px-6">
      <header>
        <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">{APP_NAME}</h1>
        <p className="mt-1 text-[var(--muted)]">
          Identifier les fonds de private equity français susceptibles d&apos;investir dans une société, classés et
          expliqués.
        </p>
      </header>
      <ScreeningApp />
      <footer className="mt-auto max-w-md pt-6">
        <HealthStatus />
      </footer>
    </main>
  );
}
