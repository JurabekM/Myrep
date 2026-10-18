import { useMutation, useQuery } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import {
  commands,
  type ConflictDto,
  type ImportPreviewDto,
  type PairingView,
  type PickedFile,
} from "../../bindings";
import { ErrorText } from "../../components/ErrorText";
import { call, CoreError } from "../../lib/api";
import { keys } from "../../lib/queryClient";

/** Yadrodagi chegara bilan bir xil (`MIN_PASSWORD_CHARS`) — faqat tugmani faollashtirish uchun. */
const MIN_PASSWORD = 8;

const when = (iso: string | null) =>
  iso ? iso.slice(0, 16).replace("T", " ") : "—";

/**
 * `.baraka` almashish (8.3–8.5): qurilmalar, shifrlangan eksport, import oldidan ko'rinish va
 * ziddiyatlarni tanlash, yangi qurilmani ulash. Birlashtirish qoidalari yadroda.
 */
export function SyncScreen() {
  const { t } = useTranslation();
  const role = useQuery({
    queryKey: keys.deviceRole,
    queryFn: () => call(commands.deviceRole()),
  });
  const owner = (role.data?.role ?? "OWNER") === "OWNER";
  return (
    <section className="flex flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("sync.title")}</h1>
      <aside className="card flex flex-col gap-2 border-accent/40">
        <p className="text-sm font-semibold text-accent-text">
          {t("mentor.name")}
        </p>
        <p>{t("sync.intro")}</p>
      </aside>
      <Devices owner={owner} />
      <Export />
      <Import />
      {owner ? (
        <Pairing />
      ) : (
        <p role="note" className="card text-sm text-ink-muted">
          {t("sync.roleNote")}
        </p>
      )}
    </section>
  );
}

function Devices({ owner }: { owner: boolean }) {
  const { t } = useTranslation();
  const q = useQuery({
    queryKey: keys.devices,
    queryFn: () => call(commands.devices()),
  });
  // Bekor qilish — ikki bosqichda (tasdiq shu yerning o'zida).
  const [confirm, setConfirm] = useState<string | null>(null);
  const revoke = useMutation({
    mutationFn: (id: string) => call(commands.revokeDevice(id)),
    onSuccess: () => setConfirm(null),
  });
  return (
    <section className="card flex flex-col gap-2">
      <h2 className="text-lg font-semibold">{t("sync.devices")}</h2>
      <ErrorText error={q.error} />
      {(q.data ?? []).map((d) => (
        <div
          key={d.id}
          className="flex flex-wrap items-center justify-between gap-2 border-b border-line pb-2 text-sm"
        >
          <span>
            <span className="font-medium">{d.name}</span>{" "}
            <span className="text-ink-muted">· {d.platform}</span>
            {d.isThis && (
              <span className="ml-2 rounded border border-accent px-2 py-0.5 text-xs text-accent-text">
                {t("sync.thisDevice")}
              </span>
            )}
            {d.role && (
              <span
                data-testid={`device-role-${d.name}`}
                className="ml-2 rounded border border-line px-2 py-0.5 text-xs"
              >
                {t(`sync.role.${d.role}`)}
                {d.revoked && ` · ${t("sync.revoked")}`}
              </span>
            )}
          </span>
          {!d.isThis && (
            <span className="text-ink-muted tabular-nums">
              {t("sync.lastImport")}: {when(d.lastImportAt)} ·{" "}
              {t("sync.lastExport")}: {when(d.lastExportAt)}
            </span>
          )}
          {owner && d.role && !d.revoked && (
            <span className="flex w-full flex-wrap items-center gap-2">
              {confirm === d.id ? (
                <>
                  <span className="text-warn">{t("sync.revokeConfirm")}</span>
                  <button
                    className="btn-ghost px-3 py-1 text-sm"
                    disabled={revoke.isPending}
                    onClick={() => revoke.mutate(d.id)}
                  >
                    {t("sync.revokeYes")}
                  </button>
                  <button
                    className="btn-ghost px-3 py-1 text-sm"
                    onClick={() => setConfirm(null)}
                  >
                    {t("common.cancel")}
                  </button>
                </>
              ) : (
                <button
                  className="btn-ghost px-3 py-1 text-sm"
                  onClick={() => setConfirm(d.id)}
                >
                  {t("sync.revoke")}
                </button>
              )}
            </span>
          )}
        </div>
      ))}
      <ErrorText error={revoke.error} />
      {(q.data ?? []).filter((d) => !d.isThis).length === 0 && (
        <p className="text-sm text-ink-muted">{t("sync.noPeers")}</p>
      )}
    </section>
  );
}

function PasswordFields({
  value,
  onChange,
  confirm,
}: {
  value: string;
  onChange: (v: string) => void;
  confirm?: { value: string; onChange: (v: string) => void };
}) {
  const { t } = useTranslation();
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <label>
        <span className="label">{t("sync.password")}</span>
        <input
          className="field"
          type="password"
          autoComplete="new-password"
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
      </label>
      {confirm && (
        <label>
          <span className="label">{t("sync.passwordRepeat")}</span>
          <input
            className="field"
            type="password"
            autoComplete="new-password"
            value={confirm.value}
            onChange={(e) => confirm.onChange(e.target.value)}
          />
        </label>
      )}
    </div>
  );
}

function Export() {
  const { t } = useTranslation();
  const devices = useQuery({
    queryKey: keys.devices,
    queryFn: () => call(commands.devices()),
  });
  const peers = (devices.data ?? []).filter((d) => !d.isThis);
  const [mode, setMode] = useState<"FULL" | "INCREMENTAL">("FULL");
  const [peer, setPeer] = useState("");
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");
  const run = useMutation({
    mutationFn: () => {
      if (pw !== pw2)
        throw new CoreError({ code: "PASSWORD_MISMATCH", field: "password" });
      return call(
        commands.exportBaraka({
          password: pw,
          mode,
          peerDeviceId:
            mode === "INCREMENTAL" ? peer || (peers[0]?.id ?? null) : null,
        }),
      );
    },
    onSuccess: (rows) => {
      if (rows !== null) {
        setPw("");
        setPw2("");
      }
    },
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    run.mutate();
  };
  return (
    <form
      className="card flex flex-col gap-3"
      onSubmit={submit}
      aria-label={t("sync.export")}
    >
      <h2 className="text-lg font-semibold">{t("sync.export")}</h2>
      <div
        role="radiogroup"
        aria-label={t("sync.mode")}
        className="flex flex-col gap-2 text-sm"
      >
        {(["FULL", "INCREMENTAL"] as const).map((m) => (
          <label key={m} className="flex items-start gap-2">
            <input
              type="radio"
              name="export-mode"
              className="mt-1"
              checked={mode === m}
              disabled={m === "INCREMENTAL" && peers.length === 0}
              onChange={() => {
                setMode(m);
                run.reset();
              }}
            />
            <span>
              <span className="font-medium">{t(`sync.mode.${m}`)}</span>
              <span className="block text-ink-muted">
                {t(`sync.modeHint.${m}`)}
              </span>
            </span>
          </label>
        ))}
      </div>
      {mode === "INCREMENTAL" && (
        <label className="max-w-sm">
          <span className="label">{t("sync.forDevice")}</span>
          <select
            className="field"
            value={peer || (peers[0]?.id ?? "")}
            onChange={(e) => setPeer(e.target.value)}
          >
            {peers.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </label>
      )}
      <PasswordFields
        value={pw}
        onChange={setPw}
        confirm={{ value: pw2, onChange: setPw2 }}
      />
      <p className="text-sm text-ink-muted">{t("sync.passwordHint")}</p>
      <ErrorText error={run.error} />
      {run.isSuccess && run.data !== null && (
        <p role="status" className="text-sm text-accent-text">
          {t("sync.exported", { count: run.data })}
        </p>
      )}
      <button
        className="btn-primary self-start"
        disabled={run.isPending || pw.length < MIN_PASSWORD}
      >
        {t("sync.saveFile")}
      </button>
    </form>
  );
}

function Import() {
  const { t } = useTranslation();
  const [file, setFile] = useState<PickedFile | null>(null);
  const [pw, setPw] = useState("");
  const [choices, setChoices] = useState<Record<string, "LOCAL" | "REMOTE">>(
    {},
  );
  const pick = useMutation({
    mutationFn: () => call(commands.pickBarakaFile()),
    onSuccess: (f) => {
      if (f) {
        setFile(f);
        inspect.reset();
        apply.reset();
        setChoices({});
      }
    },
  });
  const inspect = useMutation({
    mutationFn: () => call(commands.inspectBaraka(file?.path ?? "", pw)),
  });
  const apply = useMutation({
    mutationFn: () =>
      call(
        commands.applyBaraka(
          file?.path ?? "",
          pw,
          Object.entries(choices).map(([key, choice]) => ({ key, choice })),
        ),
      ),
    onSuccess: () => {
      inspect.reset();
      setPw("");
    },
  });
  const pv = inspect.data;
  const unresolved = pv
    ? pv.conflicts.filter((c) => !choices[c.key]).length
    : 0;
  return (
    <section className="card flex flex-col gap-3" aria-label={t("sync.import")}>
      <h2 className="text-lg font-semibold">{t("sync.import")}</h2>
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          className="btn-ghost"
          disabled={pick.isPending}
          onClick={() => pick.mutate()}
        >
          {t("sync.pickFile")}
        </button>
        <span className="text-sm text-ink-muted">
          {file ? file.name : t("sync.noFile")}
        </span>
      </div>
      {file && (
        <form
          className="flex flex-col gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            apply.reset();
            setChoices({});
            inspect.mutate();
          }}
        >
          <PasswordFields value={pw} onChange={setPw} />
          <button
            className="btn-ghost self-start"
            disabled={inspect.isPending || pw === ""}
          >
            {t("sync.inspect")}
          </button>
        </form>
      )}
      <ErrorText error={pick.error ?? inspect.error ?? apply.error} />
      {pv && (
        <Preview
          pv={pv}
          choices={choices}
          onChoose={(k, c) => setChoices({ ...choices, [k]: c })}
        />
      )}
      {pv && (
        <div className="flex flex-wrap items-center gap-3">
          <button
            className="btn-primary"
            disabled={!pv.canApply || unresolved > 0 || apply.isPending}
            onClick={() => apply.mutate()}
          >
            {t("sync.apply")}
          </button>
          {unresolved > 0 && (
            <span className="text-sm text-warn">
              {t("sync.unresolved", { count: unresolved })}
            </span>
          )}
        </div>
      )}
      {apply.data && (
        <p role="status" className="text-sm text-accent-text">
          {t("sync.applied", {
            inserted: apply.data.inserted,
            updated: apply.data.updated,
            journal: apply.data.journalAppended,
            conflicts: apply.data.conflictsLocal + apply.data.conflictsRemote,
          })}
          {apply.data.rejected > 0 &&
            ` ${t("sync.appliedRejected", { count: apply.data.rejected })}`}
        </p>
      )}
    </section>
  );
}

function Preview({
  pv,
  choices,
  onChoose,
}: {
  pv: ImportPreviewDto;
  choices: Record<string, string>;
  onChoose: (key: string, choice: "LOCAL" | "REMOTE") => void;
}) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm">
        {t("sync.from", {
          name: pv.sourceDeviceName,
          date: when(pv.exportedAt),
        })}{" "}
        · {t(`sync.mode.${pv.mode}`)}
      </p>
      <dl className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm sm:grid-cols-4">
        {(
          [
            ["inserts", pv.inserts],
            ["updates", pv.updates],
            ["journal", pv.journalAppended],
            ["same", pv.same + pv.keptLocal],
          ] as const
        ).map(([k, v]) => (
          <div key={k}>
            <dt className="text-ink-muted">{t(`sync.count.${k}`)}</dt>
            <dd className="text-lg font-semibold tabular-nums">{v}</dd>
          </div>
        ))}
      </dl>
      {pv.forks.length > 0 && (
        <div
          role="alert"
          className="flex flex-col gap-1 rounded border border-danger p-3 text-sm"
        >
          <p className="font-semibold text-danger">{t("sync.forkTitle")}</p>
          {pv.forks.map((f) => (
            <p key={`${f.agreementId}-${f.reason}`}>
              {t(`sync.fork.${f.reason}`, { title: f.title, seq: f.seq })}
            </p>
          ))}
          <p className="text-ink-muted">{t("sync.forkHint")}</p>
        </div>
      )}
      {pv.protected.length > 0 && (
        <div className="flex flex-col gap-1 rounded border border-warn p-3 text-sm">
          <p className="font-semibold text-warn">
            {t("sync.protectedTitle", { count: pv.protected.length })}
          </p>
          {pv.protected.map((p) => (
            <p key={p.key} className="text-ink-muted">
              {t(`sync.table.${p.table}`, { defaultValue: p.table })}:{" "}
              {p.label || p.rowId}
            </p>
          ))}
        </div>
      )}
      {pv.rejected.length > 0 && (
        <div
          data-testid="sync-rejected"
          className="flex flex-col gap-1 rounded border border-warn p-3 text-sm"
        >
          <p className="font-semibold text-warn">
            {t("sync.rejectedTitle", { count: pv.rejected.length })}
          </p>
          <p className="text-ink-muted">{t("sync.rejectedHint")}</p>
          {pv.rejected.map((r) => (
            <p key={r.key}>
              {t(`sync.table.${r.table}`, { defaultValue: r.table })}:{" "}
              {r.label || r.rowId} —{" "}
              <span className="text-warn">{t(`error.${r.reason}`)}</span>
            </p>
          ))}
        </div>
      )}
      {pv.ignored > 0 && (
        <p className="text-sm text-ink-muted">
          {t("sync.ignored", { count: pv.ignored })}
        </p>
      )}
      {pv.conflicts.length > 0 && (
        <div className="flex flex-col gap-3">
          <p className="font-semibold">
            {t("sync.conflictsTitle", { count: pv.conflicts.length })}
          </p>
          <p className="text-sm text-ink-muted">{t("sync.conflictsHint")}</p>
          {pv.conflicts.map((c) => (
            <Conflict
              key={c.key}
              c={c}
              choice={choices[c.key]}
              onChoose={(x) => onChoose(c.key, x)}
            />
          ))}
        </div>
      )}
      {pv.conflicts.length === 0 && pv.forks.length === 0 && (
        <p className="text-sm text-accent-text">{t("sync.noConflicts")}</p>
      )}
    </div>
  );
}

function Conflict({
  c,
  choice,
  onChoose,
}: {
  c: ConflictDto;
  choice: string | undefined;
  onChoose: (c: "LOCAL" | "REMOTE") => void;
}) {
  const { t } = useTranslation();
  return (
    <article
      aria-label={c.label || c.rowId}
      className="flex flex-col gap-2 rounded border border-warn p-3 text-sm"
    >
      <p className="font-medium">
        {t(`sync.table.${c.table}`, { defaultValue: c.table })}:{" "}
        {c.label || c.rowId}
      </p>
      <table className="w-full table-fixed text-left">
        <thead className="text-ink-muted">
          <tr>
            <th className="w-1/5 py-1 pr-3 font-normal">{t("sync.field")}</th>
            <th className="py-1 pr-3 font-normal">{t("sync.local")}</th>
            <th className="py-1 font-normal">{t("sync.remote")}</th>
          </tr>
        </thead>
        <tbody>
          {c.localDeleted !== c.remoteDeleted && (
            <tr className="border-t border-line">
              <td className="py-1 pr-3">{t("sync.state")}</td>
              <td className="py-1 pr-3">
                {t(c.localDeleted ? "sync.deleted" : "sync.kept")}
              </td>
              <td className="py-1">
                {t(c.remoteDeleted ? "sync.deleted" : "sync.kept")}
              </td>
            </tr>
          )}
          {c.fields
            .filter((f) => f.field !== "deleted_at")
            .map((f) => (
              <tr key={f.field} className="border-t border-line align-top">
                <td className="py-1 pr-3 text-ink-muted">
                  {t(`sync.col.${f.field}`, { defaultValue: f.field })}
                </td>
                <td className="py-1 pr-3 break-words tabular-nums">
                  {f.local}
                </td>
                <td className="py-1 break-words tabular-nums">{f.remote}</td>
              </tr>
            ))}
        </tbody>
      </table>
      <div
        role="radiogroup"
        aria-label={t("sync.choose")}
        className="flex flex-wrap gap-4"
      >
        {(["LOCAL", "REMOTE"] as const).map((x) => (
          <label key={x} className="flex items-center gap-2">
            <input
              type="radio"
              name={`choice-${c.key}`}
              checked={choice === x}
              onChange={() => onChoose(x)}
            />
            {t(`sync.keep.${x}`)}
          </label>
        ))}
      </div>
    </article>
  );
}

type PairRole = "FAMILY" | "SELLER" | "ACCOUNTANT";

function Pairing() {
  const { t } = useTranslation();
  const [view, setView] = useState<PairingView | null>(null);
  const household = useQuery({
    queryKey: keys.household,
    queryFn: () => call(commands.household()),
  });
  const businesses = (household.data?.spaces ?? []).filter(
    (s) => s.kind === "KASBKOR",
  );
  const [role, setRole] = useState<PairRole>("FAMILY");
  const [space, setSpace] = useState("");
  const offer = useMutation({
    mutationFn: () =>
      call(
        commands.pairingOffer(
          role === "FAMILY"
            ? { role: null, spaceId: null }
            : { role, spaceId: space || (businesses[0]?.id ?? null) },
        ),
      ),
    onSuccess: (v) => v && setView(v),
  });
  return (
    <section
      className="card flex flex-col gap-3"
      aria-label={t("sync.pairing")}
    >
      <h2 className="text-lg font-semibold">{t("sync.pairing")}</h2>
      <p className="text-sm text-ink-muted">{t("sync.pairingHint")}</p>
      <ErrorText error={offer.error} />
      {view ? (
        <div className="flex flex-wrap items-start gap-5">
          <img
            alt={t("sync.qrAlt")}
            className="h-48 w-48 rounded bg-[#FFFFFF] p-1"
            src={`data:image/svg+xml;utf8,${encodeURIComponent(view.qrSvg)}`}
          />
          <div className="flex min-w-0 flex-1 flex-col gap-2 text-sm">
            <p>{t("sync.pairingSaved", { file: view.fileName })}</p>
            {role !== "FAMILY" && (
              <p data-testid="pairing-role" className="text-accent-text">
                {t(`sync.pairingFor.${role}`)}
              </p>
            )}
            <p className="text-ink-muted">{t("sync.pairingCode")}</p>
            {/* 8 guruh: 24ch kenglikda ikki qatorga 4 tadan, chiziqcha joyida bo'linadi. */}
            <p
              data-testid="pairing-code"
              className="max-w-[24ch] font-mono text-lg tracking-wider select-all"
            >
              {view.code}
            </p>
            <p className="text-ink-muted">{t("sync.pairingSteps")}</p>
            <button
              className="btn-ghost self-start"
              onClick={() => setView(null)}
            >
              {t("common.close")}
            </button>
          </div>
        </div>
      ) : (
        <>
          <div
            role="radiogroup"
            aria-label={t("sync.pairRole")}
            className="flex flex-col gap-2 text-sm"
          >
            {(["FAMILY", "SELLER", "ACCOUNTANT"] as const).map((r) => (
              <label key={r} className="flex items-start gap-2">
                <input
                  type="radio"
                  name="pair-role"
                  className="mt-1"
                  checked={role === r}
                  disabled={r !== "FAMILY" && businesses.length === 0}
                  onChange={() => setRole(r)}
                />
                <span>
                  <span className="font-medium">{t(`sync.pairRole.${r}`)}</span>
                  <span className="block text-ink-muted">
                    {t(`sync.pairRoleHint.${r}`)}
                  </span>
                </span>
              </label>
            ))}
          </div>
          {role !== "FAMILY" && businesses.length > 1 && (
            <label className="max-w-sm">
              <span className="label">{t("sync.pairSpace")}</span>
              <select
                className="field"
                value={space || (businesses[0]?.id ?? "")}
                onChange={(e) => setSpace(e.target.value)}
              >
                {businesses.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.name}
                  </option>
                ))}
              </select>
            </label>
          )}
          <button
            className="btn-ghost self-start"
            disabled={offer.isPending}
            onClick={() => offer.mutate()}
          >
            {t("sync.pairingStart")}
          </button>
        </>
      )}
    </section>
  );
}
