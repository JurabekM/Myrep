import { type ColumnDef, flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table";
import * as echarts from "echarts/core";
import { LineChart } from "echarts/charts";
import { GridComponent, LegendComponent, TooltipComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import { type SyntheticEvent, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  type LoanDto,
  type PayoffDto,
  type ScheduleRowDto,
  commands,
} from "../../bindings/bindings";
import { unwrap } from "../finance/command-error";
import { useErrorMessage } from "../finance/errors";
import { Alert, Card, Field, PrimaryButton, Stat } from "../finance/ui";

echarts.use([LineChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer]);

const SELECT_CLASS =
  "h-10 rounded-lg border border-border bg-app px-3 text-text outline-none focus:border-accent";
const TYPES = ["ANNUITY", "DIFFERENTIATED", "FIXED_MARKUP"] as const;
type ScheduleType = (typeof TYPES)[number];

function typeKey(value: ScheduleType) {
  switch (value) {
    case "DIFFERENTIATED":
      return "payoff.type.DIFFERENTIATED" as const;
    case "FIXED_MARKUP":
      return "payoff.type.FIXED_MARKUP" as const;
    default:
      return "payoff.type.ANNUITY" as const;
  }
}

/**
 * Payoff rejalashtiruvchisi (SPEC 2D, D10): mavjud ustamali qarz uchun odatiy va tezlashtirilgan grafik,
 * «qarzsiz kun», jadval (TanStack Table) va qoldiq grafigi (ECharts). Hisob Rustda; bu yerda faqat ko'rsatish.
 * Stavka — foydalanuvchining mavjud qarzi tavsifi, «muqobil daromad» emas.
 */
export function PayoffPlannerCard({ loans = [] }: { loans?: LoanDto[] }) {
  const { t } = useTranslation();
  const openLoans = loans.filter((loan) => !loan.settled);
  const message = useErrorMessage();
  const [type, setType] = useState<ScheduleType>("ANNUITY");
  const [principal, setPrincipal] = useState("");
  const [annualPercent, setAnnualPercent] = useState("24");
  const [markup, setMarkup] = useState("");
  const [term, setTerm] = useState("12");
  const [extra, setExtra] = useState("");
  const [result, setResult] = useState<PayoffDto | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const annualBp = Math.round(Number(annualPercent) * 100);
    try {
      setResult(
        unwrap(
          await commands.simulatePayoff({
            scheduleType: type,
            principal,
            annualBp: Number.isFinite(annualBp) && annualBp >= 0 ? annualBp : 0,
            markup,
            termMonths: Number(term),
            extraPerMonth: extra,
            startDate: null,
          }),
        ),
      );
    } catch (caught) {
      setError(message(caught));
    }
  }

  return (
    <Card title={t("payoff.title")}>
      <p className="text-sm text-muted">{t("payoff.intro")}</p>
      <form className="flex flex-col gap-4" onSubmit={(event) => void run(event)}>
        {openLoans.length > 0 ? (
          <div className="flex flex-col gap-2">
            <label htmlFor="payoff-from-loan" className="text-sm text-muted">
              {t("payoff.fromLoan")}
            </label>
            <select
              id="payoff-from-loan"
              className={SELECT_CLASS}
              defaultValue=""
              onChange={(event) => {
                const loan = openLoans.find((l) => l.id === event.currentTarget.value);
                if (loan !== undefined) {
                  setPrincipal(loan.outstanding.formatted);
                  setTerm(String(Math.max(1, loan.installments)));
                  setResult(null);
                }
              }}
            >
              <option value="">{t("payoff.fromLoanNone")}</option>
              {openLoans.map((loan) => (
                <option key={loan.id} value={loan.id}>
                  {loan.counterparty} · {loan.outstanding.formatted}
                </option>
              ))}
            </select>
          </div>
        ) : null}
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="flex flex-col gap-2">
            <label htmlFor="payoff-type" className="text-sm text-muted">
              {t("payoff.typeLabel")}
            </label>
            <select
              id="payoff-type"
              className={SELECT_CLASS}
              value={type}
              onChange={(event) => {
                const value = event.currentTarget.value;
                setType(TYPES.find((k) => k === value) ?? "ANNUITY");
              }}
            >
              {TYPES.map((k) => (
                <option key={k} value={k}>
                  {t(typeKey(k))}
                </option>
              ))}
            </select>
          </div>
          <Field
            id="payoff-principal"
            label={t("payoff.principal")}
            inputMode="numeric"
            value={principal}
            onChange={(event) => {
              setPrincipal(event.currentTarget.value);
            }}
          />
          <Field
            id="payoff-term"
            label={t("payoff.term")}
            type="number"
            min={1}
            max={600}
            value={term}
            onChange={(event) => {
              setTerm(event.currentTarget.value);
            }}
          />
          {type === "FIXED_MARKUP" ? (
            <Field
              id="payoff-markup"
              label={t("payoff.markup")}
              inputMode="numeric"
              value={markup}
              onChange={(event) => {
                setMarkup(event.currentTarget.value);
              }}
            />
          ) : (
            <Field
              id="payoff-rate"
              label={t("payoff.rate")}
              inputMode="decimal"
              value={annualPercent}
              onChange={(event) => {
                setAnnualPercent(event.currentTarget.value);
              }}
            />
          )}
          <Field
            id="payoff-extra"
            label={t("payoff.extra")}
            inputMode="numeric"
            value={extra}
            onChange={(event) => {
              setExtra(event.currentTarget.value);
            }}
          />
        </div>
        <div>
          <PrimaryButton type="submit" disabled={principal.trim() === "" || Number(term) <= 0}>
            {t("payoff.simulate")}
          </PrimaryButton>
        </div>
      </form>
      {error !== null ? <Alert>{error}</Alert> : null}
      {result !== null ? <PayoffResult result={result} /> : null}
    </Card>
  );
}

function PayoffResult({ result }: { result: PayoffDto }) {
  const { t } = useTranslation();
  const chartRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const element = chartRef.current;
    if (element === null) {
      return;
    }
    const chart = echarts.init(element, undefined, { renderer: "canvas" });
    const months = Math.max(result.standard.rows.length, result.accelerated.rows.length);
    const axis = Array.from({ length: months }, (_, index) => String(index + 1));
    const toMajor = (row: ScheduleRowDto | undefined) =>
      row === undefined ? null : Number(row.balance.minor) / 100;
    chart.setOption({
      backgroundColor: "transparent",
      textStyle: { color: "#a8a29e" },
      legend: {
        data: [t("payoff.standard"), t("payoff.accelerated")],
        textStyle: { color: "#a8a29e" },
      },
      tooltip: { trigger: "axis" },
      grid: { left: 60, right: 16, top: 36, bottom: 28 },
      xAxis: { type: "category", data: axis, axisLine: { lineStyle: { color: "#57534e" } } },
      yAxis: { type: "value", splitLine: { lineStyle: { color: "#292524" } } },
      series: [
        {
          name: t("payoff.standard"),
          type: "line",
          smooth: true,
          data: axis.map((_, index) => toMajor(result.standard.rows[index])),
          lineStyle: { color: "#78716c" },
          itemStyle: { color: "#78716c" },
        },
        {
          name: t("payoff.accelerated"),
          type: "line",
          smooth: true,
          data: axis.map((_, index) => toMajor(result.accelerated.rows[index])),
          lineStyle: { color: "#d97757" },
          itemStyle: { color: "#d97757" },
        },
      ],
    });
    const resize = () => {
      chart.resize();
    };
    window.addEventListener("resize", resize);
    return () => {
      window.removeEventListener("resize", resize);
      chart.dispose();
    };
  }, [result, t]);

  return (
    <div className="flex flex-col gap-4">
      <div className="grid gap-6 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label={t("payoff.payment")} value={result.standard.payment.formatted} />
        <Stat
          label={t("payoff.debtFreeStandard")}
          value={result.standard.debtFreeDay}
          hint={t("payoff.monthsHint", { months: result.standard.months })}
        />
        <Stat
          label={t("payoff.debtFreeAccelerated")}
          value={result.accelerated.debtFreeDay}
          hint={t("payoff.monthsSaved", { months: result.monthsSaved })}
        />
        <Stat label={t("payoff.interestSaved")} value={result.interestSaved.formatted} />
      </div>
      <div ref={chartRef} role="img" aria-label={t("payoff.chartLabel")} className="h-64 w-full" />
      <ScheduleTable rows={result.accelerated.rows} />
    </div>
  );
}

function ScheduleTable({ rows }: { rows: ScheduleRowDto[] }) {
  const { t } = useTranslation();
  const columns = useMemo<ColumnDef<ScheduleRowDto>[]>(
    () => [
      { header: t("payoff.colMonth"), accessorKey: "month" },
      { header: t("payoff.colDate"), accessorKey: "date" },
      {
        header: t("payoff.colInterest"),
        accessorFn: (row) => row.interest.formatted,
        id: "interest",
      },
      {
        header: t("payoff.colPrincipal"),
        accessorFn: (row) => row.principal.formatted,
        id: "principal",
      },
      { header: t("payoff.colExtra"), accessorFn: (row) => row.extra.formatted, id: "extra" },
      { header: t("payoff.colBalance"), accessorFn: (row) => row.balance.formatted, id: "balance" },
    ],
    [t],
  );
  const table = useReactTable({ data: rows, columns, getCoreRowModel: getCoreRowModel() });
  return (
    <div className="max-h-80 overflow-auto rounded-lg border border-border">
      <table className="w-full text-sm">
        <thead className="sticky top-0 bg-raised text-left text-xs text-subtle">
          {table.getHeaderGroups().map((group) => (
            <tr key={group.id}>
              {group.headers.map((header) => (
                <th key={header.id} className="px-3 py-2">
                  {flexRender(header.column.columnDef.header, header.getContext())}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr key={row.id} className="border-t border-border">
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} className="px-3 py-2 text-text">
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
