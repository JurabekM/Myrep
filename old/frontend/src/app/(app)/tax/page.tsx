"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";
import { api } from "@/lib/api-client";
import { Markdown } from "@/components/shared/Markdown";

const fmt = (n: number) => new Intl.NumberFormat("uz-UZ").format(Math.round(n));

interface BreakdownLine {
  name: string;
  base: number;
  rate: number;
  amount: number;
  note?: string;
}

interface TaxResult {
  regime: string;
  total_tax: number;
  effective_rate: number;
  lines: BreakdownLine[];
  warnings: string[];
}

interface CompareResult {
  turnover: TaxResult;
  general: TaxResult;
  recommended: string;
  savings: number;
  disclaimer: string;
  explanation?: string;
}

interface PayrollResult {
  gross: number;
  income_tax: number;
  social_tax: number;
  net_salary: number;
  employer_total_cost: number;
  disclaimer: string;
}

function ResultTable({ result }: { result: TaxResult }) {
  return (
    <div className="space-y-2 text-sm">
      <table className="w-full">
        <tbody>
          {result.lines.map((line) => (
            <tr key={line.name} className="border-b last:border-0">
              <td className="py-2">
                {line.name}
                {line.note && (
                  <p className="text-xs text-muted-foreground">{line.note}</p>
                )}
              </td>
              <td className="py-2 text-right text-muted-foreground">
                {(line.rate * 100).toFixed(0)}%
              </td>
              <td className="py-2 text-right font-medium">{fmt(line.amount)} so'm</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="flex justify-between border-t pt-2 font-semibold">
        <span>Jami soliq</span>
        <span>
          {fmt(result.total_tax)} so'm{" "}
          <span className="text-xs font-normal text-muted-foreground">
            (samarali stavka {(result.effective_rate * 100).toFixed(1)}%)
          </span>
        </span>
      </div>
      {result.warnings.map((w) => (
        <p key={w} className="rounded-lg bg-amber-50 p-2 text-xs text-amber-800 dark:bg-amber-900/20 dark:text-amber-300">
          ⚠️ {w}
        </p>
      ))}
    </div>
  );
}

export default function TaxPage() {
  const [revenue, setRevenue] = useState("");
  const [expenses, setExpenses] = useState("");
  const [salary, setSalary] = useState("");
  const [explain, setExplain] = useState(false);
  const [compareResult, setCompareResult] = useState<CompareResult | null>(null);
  const [payrollResult, setPayrollResult] = useState<PayrollResult | null>(null);
  const [loading, setLoading] = useState<"compare" | "payroll" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const compare = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading("compare");
    setError(null);
    try {
      const data = await api<CompareResult>("/tax/compare", {
        method: "POST",
        body: JSON.stringify({
          annual_revenue: Number(revenue),
          deductible_expenses: Number(expenses || 0),
          explain,
        }),
      });
      setCompareResult(data);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(null);
    }
  };

  const payroll = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading("payroll");
    setError(null);
    try {
      const data = await api<PayrollResult>("/tax/payroll", {
        method: "POST",
        body: JSON.stringify({ gross_monthly_salary: Number(salary) }),
      });
      setPayrollResult(data);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold">Soliq Kalkulyatori</h1>
        <p className="text-sm text-muted-foreground">
          Raqamlar deterministik hisoblanadi — AI faqat tushuntiradi
        </p>
      </div>

      {error && <p className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">{error}</p>}

      {/* Rejim taqqoslash */}
      <section className="rounded-2xl border p-5">
        <h2 className="mb-3 font-semibold">Soliq rejimini taqqoslash</h2>
        <form onSubmit={compare} className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block text-sm">
              Yillik aylanma (so'm)
              <input
                type="number"
                required
                min={1}
                value={revenue}
                onChange={(e) => setRevenue(e.target.value)}
                placeholder="500000000"
                className="mt-1 w-full rounded-lg border bg-background px-3 py-2"
              />
            </label>
            <label className="block text-sm">
              Yillik xarajatlar (so'm)
              <input
                type="number"
                min={0}
                value={expenses}
                onChange={(e) => setExpenses(e.target.value)}
                placeholder="200000000"
                className="mt-1 w-full rounded-lg border bg-background px-3 py-2"
              />
            </label>
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={explain}
              onChange={(e) => setExplain(e.target.checked)}
            />
            AI tushuntirishi bilan
          </label>
          <button
            type="submit"
            disabled={loading === "compare"}
            className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-primary-foreground disabled:opacity-50"
          >
            {loading === "compare" && <Loader2 size={16} className="animate-spin" />}
            Hisoblash
          </button>
        </form>

        {compareResult && (
          <div className="mt-5 space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              {(["turnover", "general"] as const).map((key) => (
                <div
                  key={key}
                  className={`rounded-xl border p-4 ${
                    compareResult.recommended === key ? "border-primary ring-1 ring-primary" : ""
                  }`}
                >
                  <h3 className="mb-2 flex items-center justify-between text-sm font-semibold">
                    {key === "turnover" ? "Aylanma soliq" : "Umumiy rejim (QQS + foyda)"}
                    {compareResult.recommended === key && (
                      <span className="rounded-full bg-primary px-2 py-0.5 text-xs text-primary-foreground">
                        Tavsiya
                      </span>
                    )}
                  </h3>
                  <ResultTable result={compareResult[key]} />
                </div>
              ))}
            </div>
            <p className="text-sm text-muted-foreground">
              Farq: <strong>{fmt(compareResult.savings)} so'm</strong> yiliga
            </p>
            {compareResult.explanation && (
              <div className="rounded-xl border p-4">
                <Markdown>{compareResult.explanation}</Markdown>
              </div>
            )}
            <p className="text-xs text-amber-800 dark:text-amber-300">{compareResult.disclaimer}</p>
          </div>
        )}
      </section>

      {/* Ish haqi */}
      <section className="rounded-2xl border p-5">
        <h2 className="mb-3 font-semibold">Ish haqi soliqlari</h2>
        <form onSubmit={payroll} className="flex flex-wrap items-end gap-3">
          <label className="block text-sm">
            Oylik ish haqi, gross (so'm)
            <input
              type="number"
              required
              min={1}
              value={salary}
              onChange={(e) => setSalary(e.target.value)}
              placeholder="10000000"
              className="mt-1 w-full rounded-lg border bg-background px-3 py-2"
            />
          </label>
          <button
            type="submit"
            disabled={loading === "payroll"}
            className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-primary-foreground disabled:opacity-50"
          >
            {loading === "payroll" && <Loader2 size={16} className="animate-spin" />}
            Hisoblash
          </button>
        </form>

        {payrollResult && (
          <div className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
            {[
              ["JShDS (12%)", payrollResult.income_tax],
              ["Ijtimoiy soliq (12%)", payrollResult.social_tax],
              ["Qo'lga tegadigan (net)", payrollResult.net_salary],
              ["Ish beruvchi xarajati", payrollResult.employer_total_cost],
            ].map(([label, value]) => (
              <div key={label as string} className="rounded-xl border p-3">
                <p className="text-xs text-muted-foreground">{label as string}</p>
                <p className="font-semibold">{fmt(value as number)} so'm</p>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
