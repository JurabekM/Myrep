import { Fragment, useState } from "react";
import { call, usePoll, type PolicyRow } from "../api";
import { ErrorBanner, VerdictPill } from "../components";

interface PoliciesResp {
  ok: boolean;
  error?: string | null;
  sources?: string[];
  policies?: PolicyRow[];
}

/** Yuklangan Cedar siyosatlari (o'qish rejimi; muharrir F5+). */
export function PoliciesScreen() {
  const { data, error } = usePoll(() => call<PoliciesResp>("policies"), 5000);
  const [open, setOpen] = useState<string | null>(null);
  if (error) return <ErrorBanner text={error} />;
  const rows = data?.policies ?? [];
  return (
    <div className="page">
      {data?.error && <ErrorBanner text={`Foydalanuvchi siyosatlari yuklanmadi, standart to'plam ishlamoqda: ${data.error}`} />}
      <p className="dim" style={{ marginTop: 0 }}>
        Manbalar: <span className="mono">{(data?.sources ?? []).join(", ")}</span>. O'z siyosatingizni{" "}
        <span className="mono">&lt;TAMGA_HOME&gt;/policies/*.cedar</span> ga qo'shing: daemon qayta ishga tushganda yuklanadi.
      </p>
      <table className="table">
        <thead>
          <tr>
            <th>Siyosat</th>
            <th>Qaror</th>
            <th>Sabab</th>
            <th>Manba</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((p) => (
            <Fragment key={p.id}>
              <tr
                className="clickable"
                role="button"
                tabIndex={0}
                aria-expanded={open === p.id}
                aria-label={`${p.id} siyosati matni`}
                onClick={() => setOpen(open === p.id ? null : p.id)}
                onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && setOpen(open === p.id ? null : p.id)}
              >
                <td className="mono">{p.id}</td>
                <td>
                  <VerdictPill verdict={p.verdict} />
                </td>
                <td>{p.reason || <span className="dim">—</span>}</td>
                <td className="mono dim">{p.source}</td>
              </tr>
              {open === p.id && (
                <tr>
                  <td colSpan={4}>
                    <div className="codeblock mono">{p.text}</div>
                  </td>
                </tr>
              )}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}
