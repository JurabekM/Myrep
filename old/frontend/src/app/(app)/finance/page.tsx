"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";
import { api } from "@/lib/api-client";

const fmt = (n: number) => new Intl.NumberFormat("uz-UZ").format(Math.round(n));

interface LoanRow {
  month: number;
  payment: number;
  principal: number;
  interest: number;
  balance: number;
}

interface LoanResult {
  monthly_payment: number;
  total_paid: number;
  total_interest: number;
  schedule: LoanRow[];
}

interface BreakEvenResult {
  units: number;
  revenue: number;
  contribution_margin: number;
}

export default function FinancePage() {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<string | null>(null);

  // Loan
  const [loan, setLoan] = useState({ principal: "", rate: "", months: "" });
  const [loanResult, setLoanResult] = useState<LoanResult | null>(null);

  // Break-even
  const [be, setBe] = useState({ fixed: "", price: "", variable: "" });
  const [beResult, setBeResult] = useState<BreakEvenResult | null>(null);

  // NPV / IRR
  const [rate, setRate] = useState("15");
  const [flows, setFlows] = useState("-100000000, 30000000, 40000000, 50000000, 60000000");
  const [npvResult, setNpvResult] = useState<number | null>(null);
  const [irrResult, setIrrResult] = useState<number | null>(null);

  const run = async (key: string, fn: () => Promise<void>) => {
    setLoading(key);
    setError(null);
    try {
      await fn();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(null);
    }
  };

  const calcLoan = () =>
    run("loan", async () => {
      const data = await api<LoanResult>("/finance/loan", {
        method: "POST",
        body: JSON.stringify({
          principal: Number(loan.principal),
          annual_rate: Number(loan.rate) / 100,
          months: Number(loan.months),
        }),
      });
      setLoanResult(data);
    });

  const calcBreakEven = () =>
    run("be", async () => {
      const data = await api<BreakEvenResult>("/finance/break-even", {
        method: "POST",
        body: JSON.stringify({
          fixed_costs: Number(be.fixed),
          price_per_unit: Number(be.price),
          variable_cost_per_unit: Number(be.variable),
        }),
      });
      setBeResult(data);
    });

  const parseFlows = () => flows.split(",").map((s) => Number(s.trim())).filter((n) => !isNaN(n));

  const calcNpvIrr = () =>
    run("npv", async () => {
      const cashFlows = parseFlows();
      const [npvData, irrData] = await Promise.all([
        api<{ npv: number }>("/finance/npv", {
          method: "POST",
          body: JSON.stringify({ rate: Number(rate) / 100, cash_flows: cashFlows }),
        }),
        api<{ irr: number }>("/finance/irr", {
          method: "POST",
          body: JSON.stringify({ cash_flows: cashFlows }),
        }).catch(() => ({ irr: NaN })),
      ]);
      setNpvResult(npvData.npv);
      setIrrResult(irrData.irr);
    });

  const input = "mt-1 w-full rounded-lg border bg-background px-3 py-2";
  const btn =
    "flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm text-primary-foreground disabled:opacity-50";

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold">Moliyaviy Kalkulyatorlar</h1>
        <p className="text-sm text-muted-foreground">
          Kredit, zararsizlik nuqtasi, NPV va IRR — aniq formulalar asosida
        </p>
      </div>

      {error && <p className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">{error}</p>}

      {/* Kredit */}
      <section className="rounded-2xl border p-5">
        <h2 className="mb-3 font-semibold">Kredit kalkulyatori (annuitet)</h2>
        <div className="grid gap-3 sm:grid-cols-3">
          <label className="text-sm">
            Kredit summasi (so'm)
            <input type="number" value={loan.principal} className={input}
              onChange={(e) => setLoan({ ...loan, principal: e.target.value })} placeholder="100000000" />
          </label>
          <label className="text-sm">
            Yillik stavka (%)
            <input type="number" step="0.1" value={loan.rate} className={input}
              onChange={(e) => setLoan({ ...loan, rate: e.target.value })} placeholder="24" />
          </label>
          <label className="text-sm">
            Muddat (oy)
            <input type="number" value={loan.months} className={input}
              onChange={(e) => setLoan({ ...loan, months: e.target.value })} placeholder="24" />
          </label>
        </div>
        <button onClick={calcLoan} disabled={loading === "loan"} className={`${btn} mt-3`}>
          {loading === "loan" && <Loader2 size={14} className="animate-spin" />}
          Hisoblash
        </button>

        {loanResult && (
          <div className="mt-4 space-y-3">
            <div className="grid gap-3 text-sm sm:grid-cols-3">
              {[
                ["Oylik to'lov", loanResult.monthly_payment],
                ["Jami to'lov", loanResult.total_paid],
                ["Jami foiz", loanResult.total_interest],
              ].map(([label, value]) => (
                <div key={label as string} className="rounded-xl border p-3">
                  <p className="text-xs text-muted-foreground">{label as string}</p>
                  <p className="font-semibold">{fmt(value as number)} so'm</p>
                </div>
              ))}
            </div>
            <details className="text-sm">
              <summary className="cursor-pointer text-muted-foreground">
                To'lov jadvali ({loanResult.schedule.length} oy)
              </summary>
              <div className="mt-2 max-h-64 overflow-y-auto rounded-lg border">
                <table className="w-full text-xs">
                  <thead className="sticky top-0 bg-muted">
                    <tr>
                      <th className="p-2 text-left">Oy</th>
                      <th className="p-2 text-right">To'lov</th>
                      <th className="p-2 text-right">Asosiy qarz</th>
                      <th className="p-2 text-right">Foiz</th>
                      <th className="p-2 text-right">Qoldiq</th>
                    </tr>
                  </thead>
                  <tbody>
                    {loanResult.schedule.map((row) => (
                      <tr key={row.month} className="border-t">
                        <td className="p-2">{row.month}</td>
                        <td className="p-2 text-right">{fmt(row.payment)}</td>
                        <td className="p-2 text-right">{fmt(row.principal)}</td>
                        <td className="p-2 text-right">{fmt(row.interest)}</td>
                        <td className="p-2 text-right">{fmt(row.balance)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          </div>
        )}
      </section>

      {/* Break-even */}
      <section className="rounded-2xl border p-5">
        <h2 className="mb-3 font-semibold">Zararsizlik nuqtasi (Break-even)</h2>
        <div className="grid gap-3 sm:grid-cols-3">
          <label className="text-sm">
            Doimiy xarajatlar (oylik, so'm)
            <input type="number" value={be.fixed} className={input}
              onChange={(e) => setBe({ ...be, fixed: e.target.value })} placeholder="50000000" />
          </label>
          <label className="text-sm">
            Birlik narxi (so'm)
            <input type="number" value={be.price} className={input}
              onChange={(e) => setBe({ ...be, price: e.target.value })} placeholder="100000" />
          </label>
          <label className="text-sm">
            Birlik o'zgaruvchan xarajati (so'm)
            <input type="number" value={be.variable} className={input}
              onChange={(e) => setBe({ ...be, variable: e.target.value })} placeholder="60000" />
          </label>
        </div>
        <button onClick={calcBreakEven} disabled={loading === "be"} className={`${btn} mt-3`}>
          {loading === "be" && <Loader2 size={14} className="animate-spin" />}
          Hisoblash
        </button>

        {beResult && (
          <div className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
            <div className="rounded-xl border p-3">
              <p className="text-xs text-muted-foreground">Zararsizlik hajmi</p>
              <p className="font-semibold">{fmt(beResult.units)} dona/oy</p>
            </div>
            <div className="rounded-xl border p-3">
              <p className="text-xs text-muted-foreground">Zararsizlik aylanmasi</p>
              <p className="font-semibold">{fmt(beResult.revenue)} so'm/oy</p>
            </div>
            <div className="rounded-xl border p-3">
              <p className="text-xs text-muted-foreground">Marja (birlik)</p>
              <p className="font-semibold">{fmt(beResult.contribution_margin)} so'm</p>
            </div>
          </div>
        )}
      </section>

      {/* NPV / IRR */}
      <section className="rounded-2xl border p-5">
        <h2 className="mb-3 font-semibold">Investitsiya bahosi (NPV / IRR)</h2>
        <div className="space-y-3">
          <label className="block text-sm">
            Pul oqimlari, vergul bilan{" "}
            <span className="text-muted-foreground">(birinchisi — investitsiya, manfiy)</span>
            <input value={flows} onChange={(e) => setFlows(e.target.value)} className={input} />
          </label>
          <label className="block text-sm sm:w-48">
            Diskont stavkasi (%)
            <input type="number" step="0.1" value={rate}
              onChange={(e) => setRate(e.target.value)} className={input} />
          </label>
          <button onClick={calcNpvIrr} disabled={loading === "npv"} className={btn}>
            {loading === "npv" && <Loader2 size={14} className="animate-spin" />}
            Hisoblash
          </button>
        </div>

        {npvResult !== null && (
          <div className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
            <div className="rounded-xl border p-3">
              <p className="text-xs text-muted-foreground">NPV</p>
              <p className={`font-semibold ${npvResult >= 0 ? "text-emerald-600" : "text-destructive"}`}>
                {fmt(npvResult)} so'm {npvResult >= 0 ? "(foydali)" : "(zarar)"}
              </p>
            </div>
            <div className="rounded-xl border p-3">
              <p className="text-xs text-muted-foreground">IRR</p>
              <p className="font-semibold">
                {irrResult !== null && !isNaN(irrResult)
                  ? `${(irrResult * 100).toFixed(1)}% yillik`
                  : "Hisoblab bo'lmadi"}
              </p>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
