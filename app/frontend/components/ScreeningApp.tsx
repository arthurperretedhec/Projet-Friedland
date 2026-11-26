"use client";

import { useState } from "react";

import { RankingResults } from "@/components/RankingResults";
import { ScreeningForm } from "@/components/ScreeningForm";
import {
  EMPTY_FORM,
  type FieldErrors,
  type FormValues,
  interpretScore,
  SECTOR_EN,
  type ScoreResponse,
  validateForm,
} from "@/lib/score";

type State =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "ok"; data: ScoreResponse; website: string; sector: string }
  | { kind: "error"; message: string };

// Champs de l'API -> champs du formulaire, pour afficher une erreur du serveur sous le bon champ.
const API_FIELDS: Record<string, keyof FormValues> = {
  company_name: "companyName",
  sector: "sector",
  deal_type: "dealType",
  stake_sought: "stake",
  enterprise_value_eur_m: "enterpriseValue",
  equity_ticket_eur_m: "equityTicket",
};

/** L'écran de screening : le formulaire, l'appel à POST /api/score et le classement. */
export function ScreeningApp() {
  const [values, setValues] = useState<FormValues>(EMPTY_FORM);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [state, setState] = useState<State>({ kind: "idle" });

  // Une erreur disparaît dès que l'utilisateur modifie le champ concerné.
  const change = (next: FormValues) => {
    const changed = (Object.keys(next) as (keyof FormValues)[]).filter((k) => next[k] !== values[k]);
    if (changed.some((k) => errors[k])) {
      const rest = { ...errors };
      for (const k of changed) delete rest[k];
      setErrors(rest);
    }
    setValues(next);
  };

  const run = async () => {
    const checked = validateForm(values);
    if (!checked.ok) {
      setErrors(checked.errors);
      return;
    }
    setErrors({});
    setState({ kind: "loading" });
    const website = values.website.trim();
    try {
      const res = await fetch("/api/score", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(checked.request),
        cache: "no-store",
      });
      const body: unknown = await res.json().catch(() => null);
      const result = interpretScore(res.status, body);
      if (result.kind === "ok") {
        setState({ kind: "ok", data: result.data, website, sector: checked.request.sector });
        return;
      }
      const fieldErrors: FieldErrors = {};
      for (const d of result.details) {
        const field = API_FIELDS[d.field];
        if (field) fieldErrors[field] = d.message;
      }
      setErrors(fieldErrors);
      setState({ kind: "error", message: result.message });
    } catch {
      const result = interpretScore(null, null);
      setState({ kind: "error", message: result.kind === "error" ? result.message : "" });
    }
  };

  return (
    <div className="grid items-start gap-6 lg:grid-cols-[340px_minmax(0,1fr)]">
      <ScreeningForm values={values} errors={errors} busy={state.kind === "loading"} onChange={change} onSubmit={() => void run()} />
      <div aria-live="polite">
        {state.kind === "idle" && (
          <div className="border-l border-[var(--accent)] p-6 text-sm text-[var(--foreground)]">
            <p className="label-caps !text-[var(--accent-text)]">Comment ça marche</p>
            <ol className="mt-2 list-decimal space-y-1 pl-5">
              <li>Décrivez la cible et l&apos;opération à gauche.</li>
              <li>
                Les fonds qui ne peuvent pas faire le deal (type d&apos;opération, ticket, position) sont écartés, avec la
                raison.
              </li>
              <li>Les autres sont notés sur 100, regroupés par société de gestion et classés en tiers.</li>
              <li>Cochez ou décochez les fonds à mettre dans le PowerPoint ; ajoutez au besoin un fonds écarté, et marquez d&apos;une étoile ceux qui ont exprimé un intérêt.</li>
              <li>Cliquez sur un fonds pour voir l&apos;aperçu de son bandeau, le détail du score et les sources.</li>
            </ol>
          </div>
        )}
        {state.kind === "loading" && (
          <p role="status" className="border border-[var(--border)] p-6 text-sm text-[var(--muted)]">
            Classement des fonds en cours…
          </p>
        )}
        {state.kind === "error" && (
          <p role="alert" data-testid="score-error" className=" border-l-4 border-[var(--error)] bg-[var(--surface)] px-3 py-2 text-sm">
            <span className="font-semibold text-[var(--error)]">Erreur</span> : {state.message}
          </p>
        )}
        {state.kind === "ok" && <RankingResults data={state.data} website={state.website} sectorLabel={SECTOR_EN[state.sector] ?? state.sector} />}
      </div>
    </div>
  );
}
