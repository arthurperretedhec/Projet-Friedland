"use client";

import { type FormEvent, useId } from "react";

import {
  DEAL_TYPES,
  type FieldErrors,
  type FormValues,
  SECTORS,
  STAKES,
  ticketShareOfEv,
} from "@/lib/score";

type Props = {
  values: FormValues;
  errors: FieldErrors;
  busy: boolean;
  onChange: (values: FormValues) => void;
  onSubmit: () => void;
};

const input =
  "w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-[var(--focus)] aria-[invalid=true]:border-[var(--error)]";

function FieldError({ id, message }: { id: string; message?: string }) {
  if (!message) return null;
  return (
    <p id={id} className="mt-1 text-xs text-[var(--error)]">
      {message}
    </p>
  );
}

/** Choix exclusifs présentés en boutons (plus rapide qu'un menu déroulant pour 2 à 5 options). */
function Segmented({
  legend,
  name,
  options,
  value,
  onSelect,
  error,
}: {
  legend: string;
  name: string;
  options: readonly { value: string; label: string; hint: string }[];
  value: string;
  onSelect: (value: string) => void;
  error?: string;
}) {
  const errorId = useId();
  const selected = options.find((o) => o.value === value);
  return (
    <fieldset aria-describedby={error ? errorId : undefined}>
      <legend className="mb-1.5 text-sm font-medium">{legend}</legend>
      <div className="flex flex-wrap gap-1.5">
        {options.map((option) => (
          <label
            key={option.value}
            className="cursor-pointer rounded-md border border-[var(--border)] px-3 py-1.5 text-sm has-[:checked]:border-[var(--accent)] has-[:checked]:bg-[var(--accent-soft)] has-[:checked]:font-semibold has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-[var(--focus)]"
          >
            <input
              type="radio"
              name={name}
              value={option.value}
              checked={value === option.value}
              onChange={() => onSelect(option.value)}
              className="sr-only"
            />
            {option.label}
          </label>
        ))}
      </div>
      {selected && <p className="mt-1 text-xs text-[var(--muted)]">{selected.hint}</p>}
      <FieldError id={errorId} message={error} />
    </fieldset>
  );
}

export function ScreeningForm({ values, errors, busy, onChange, onSubmit }: Props) {
  const set = <K extends keyof FormValues>(key: K, value: FormValues[K]) => onChange({ ...values, [key]: value });
  const share = ticketShareOfEv(values);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    onSubmit();
  };

  return (
    <form
      onSubmit={submit}
      noValidate
      aria-labelledby="form-heading"
      className="flex flex-col gap-5 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-5"
    >
      <h2 id="form-heading" className="text-lg font-semibold">
        Décrire la cible
      </h2>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="company-name" className="mb-1.5 block text-sm font-medium">
            Nom de la société
          </label>
          <input
            id="company-name"
            className={input}
            value={values.companyName}
            onChange={(e) => set("companyName", e.target.value)}
            placeholder="Ex. Groupe Durand Industrie"
            autoComplete="off"
            aria-invalid={!!errors.companyName}
            aria-describedby={errors.companyName ? "company-name-error" : undefined}
          />
          <FieldError id="company-name-error" message={errors.companyName} />
        </div>
        <div>
          <label htmlFor="website" className="mb-1.5 block text-sm font-medium">
            Site internet <span className="font-normal text-[var(--muted)]">(facultatif)</span>
          </label>
          <input
            id="website"
            type="url"
            className={input}
            value={values.website}
            onChange={(e) => set("website", e.target.value)}
            placeholder="www.exemple.fr"
            autoComplete="off"
          />
        </div>
        <div className="sm:col-span-2">
          <label htmlFor="sector" className="mb-1.5 block text-sm font-medium">
            Secteur
          </label>
          <select
            id="sector"
            className={input}
            value={values.sector}
            onChange={(e) => set("sector", e.target.value)}
            aria-invalid={!!errors.sector}
            aria-describedby={errors.sector ? "sector-error" : undefined}
          >
            <option value="">Choisir un secteur…</option>
            {SECTORS.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
          <FieldError id="sector-error" message={errors.sector} />
        </div>
      </div>

      <h2 className="border-t border-[var(--border)] pt-4 text-lg font-semibold">L&apos;opération</h2>

      <Segmented
        legend="Type d'opération"
        name="deal-type"
        options={DEAL_TYPES}
        value={values.dealType}
        onSelect={(v) => set("dealType", v)}
        error={errors.dealType}
      />
      <Segmented
        legend="Position recherchée par l'investisseur"
        name="stake"
        options={STAKES}
        value={values.stake}
        onSelect={(v) => set("stake", v)}
        error={errors.stake}
      />

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="ev" className="mb-1.5 block text-sm font-medium">
            Valeur d&apos;entreprise (M€)
          </label>
          <input
            id="ev"
            inputMode="decimal"
            className={`${input} tabular-nums`}
            value={values.enterpriseValue}
            onChange={(e) => set("enterpriseValue", e.target.value)}
            placeholder="Ex. 40"
            aria-invalid={!!errors.enterpriseValue}
            aria-describedby={errors.enterpriseValue ? "ev-error" : undefined}
          />
          <FieldError id="ev-error" message={errors.enterpriseValue} />
        </div>
        <div>
          <label htmlFor="ticket" className="mb-1.5 block text-sm font-medium">
            Ticket equity recherché (M€)
          </label>
          <input
            id="ticket"
            inputMode="decimal"
            className={`${input} tabular-nums`}
            value={values.equityTicket}
            onChange={(e) => set("equityTicket", e.target.value)}
            placeholder="Ex. 15"
            aria-invalid={!!errors.equityTicket}
            aria-describedby={errors.equityTicket ? "ticket-error" : "ticket-hint"}
          />
          <FieldError id="ticket-error" message={errors.equityTicket} />
          {!errors.equityTicket && (
            <p id="ticket-hint" className="mt-1 text-xs text-[var(--muted)]">
              {share === null ? "Fonds propres apportés par l'investisseur" : `Soit ${share} % de la VE`}
            </p>
          )}
        </div>
      </div>

      <button
        type="submit"
        disabled={busy}
        className="rounded-md bg-[var(--accent)] px-4 py-2.5 text-sm font-semibold text-[var(--on-accent)] hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--focus)] disabled:opacity-60"
      >
        {busy ? "Classement en cours…" : "Trouver les acquéreurs"}
      </button>
    </form>
  );
}
