import { useQuery, useQueryClient } from "@tanstack/react-query";
import { type SyntheticEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { type PriceItemDto, type PricesDto, commands } from "../../bindings/bindings";
import { unwrap } from "../finance/command-error";
import { useErrorMessage } from "../finance/errors";
import { financeKeys } from "../finance/queries";
import {
  Alert,
  Card,
  Field,
  PageHeader,
  PrimaryButton,
  SecondaryButton,
  Stat,
} from "../finance/ui";

/** bp → «+62,5 %» ko'rinishi (faqat ko'rsatish; hisob Rustda). */
export function bpText(bp: number): string {
  const sign = bp > 0 ? "+" : bp < 0 ? "−" : "";
  const abs = Math.abs(bp);
  return `${sign}${String(Math.floor(abs / 100))},${String(Math.floor((abs % 100) / 10))} %`;
}

/**
 * «Narx daftari» (SPEC 2C.2): mahsulot narxlari, shaxsiy inflyatsiya indeksi va «Sichqon kemirgani» —
 * yotgan pulning bugungi narxlardagi qiymati. Maqsad qo'rqitish emas, tushuntirish.
 */
export function PricesPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const message = useErrorMessage();
  const prices = useQuery({
    queryKey: financeKeys.prices,
    queryFn: () => commands.getPrices().then(unwrap),
  });
  const [name, setName] = useState("");
  const [basePrice, setBasePrice] = useState("");
  const [currentPrice, setCurrentPrice] = useState("");
  const [weight, setWeight] = useState("10");
  const [error, setError] = useState<string | null>(null);

  function apply(next: PricesDto) {
    queryClient.setQueryData(financeKeys.prices, next);
  }

  async function run(action: () => Promise<PricesDto>, onDone?: () => void) {
    setError(null);
    try {
      apply(await action());
      onDone?.();
    } catch (caught) {
      setError(message(caught));
    }
  }

  function add(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    const weightBp = Math.round(Number(weight) * 100);
    void run(
      () =>
        commands
          .addPriceItem({
            name,
            basePrice,
            currentPrice,
            weightBp: Number.isFinite(weightBp) ? weightBp : 0,
          })
          .then(unwrap),
      () => {
        setName("");
        setBasePrice("");
        setCurrentPrice("");
      },
    );
  }

  return (
    <div className="flex flex-col gap-8">
      <PageHeader title={t("nav.prices")} subtitle={t("prices.subtitle")} />
      {prices.isError ? <Alert>{t("errors.generic")}</Alert> : null}
      {prices.isSuccess ? (
        <>
          <Card title={t("prices.mouseTitle")}>
            <p className="text-sm text-muted">{t("prices.mouseIntro")}</p>
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              <Stat label={t("prices.nominal")} value={prices.data.balance.formatted} />
              <Stat
                label={t("prices.index")}
                value={prices.data.indexBp === null ? "—" : bpText(prices.data.indexBp)}
                hint={t("prices.indexHint")}
              />
              <Stat
                label={t("prices.realValue")}
                value={prices.data.realValue?.formatted ?? "—"}
                hint={t("prices.realValueHint")}
              />
            </div>
            {prices.data.exampleName !== null &&
            prices.data.exampleUnitsBefore !== null &&
            prices.data.exampleUnitsNow !== null ? (
              <p className="text-sm text-text">
                {t("prices.example", {
                  name: prices.data.exampleName,
                  before: prices.data.exampleUnitsBefore,
                  now: prices.data.exampleUnitsNow,
                })}
              </p>
            ) : null}
            <p className="text-xs text-subtle">{t("prices.nextStep")}</p>
          </Card>

          <Card title={t("prices.itemsTitle")}>
            {prices.data.items.length === 0 ? (
              <p className="text-sm text-muted">{t("prices.empty")}</p>
            ) : (
              <ul className="flex flex-col gap-2">
                {prices.data.items.map((item) => (
                  <PriceRow
                    key={item.id}
                    item={item}
                    onUpdate={(value) => {
                      void run(() => commands.updatePrice(item.id, value).then(unwrap));
                    }}
                    onRemove={() => {
                      void run(() => commands.removePriceItem(item.id).then(unwrap));
                    }}
                  />
                ))}
              </ul>
            )}
            <form className="flex flex-col gap-4" onSubmit={add}>
              <Field
                id="price-name"
                label={t("prices.name")}
                value={name}
                onChange={(event) => {
                  setName(event.currentTarget.value);
                }}
              />
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <Field
                  id="price-base"
                  label={t("prices.basePrice")}
                  inputMode="numeric"
                  value={basePrice}
                  onChange={(event) => {
                    setBasePrice(event.currentTarget.value);
                  }}
                />
                <Field
                  id="price-current"
                  label={t("prices.currentPrice")}
                  inputMode="numeric"
                  value={currentPrice}
                  onChange={(event) => {
                    setCurrentPrice(event.currentTarget.value);
                  }}
                />
                <Field
                  id="price-weight"
                  label={t("prices.weight")}
                  inputMode="numeric"
                  value={weight}
                  onChange={(event) => {
                    setWeight(event.currentTarget.value);
                  }}
                />
              </div>
              <div>
                <PrimaryButton
                  type="submit"
                  disabled={
                    name.trim() === "" || basePrice.trim() === "" || currentPrice.trim() === ""
                  }
                >
                  {t("prices.add")}
                </PrimaryButton>
              </div>
            </form>
            {error !== null ? <Alert>{error}</Alert> : null}
          </Card>
        </>
      ) : null}
    </div>
  );
}

function PriceRow({
  item,
  onUpdate,
  onRemove,
}: {
  item: PriceItemDto;
  onUpdate: (value: string) => void;
  onRemove: () => void;
}) {
  const { t } = useTranslation();
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState("");

  return (
    <li className="flex flex-col gap-3 rounded-lg border border-border bg-app px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
      <span className="flex flex-col gap-1">
        <span className="text-sm text-text">{item.name}</span>
        <span className="text-xs text-subtle">
          {item.basePrice.formatted} → {item.currentPrice.formatted}
          {item.changeBp !== null ? ` · ${bpText(item.changeBp)}` : ""} ·{" "}
          {t("prices.weightShort", { percent: item.weightBp / 100 })}
        </span>
      </span>
      <span className="flex flex-wrap items-center gap-2">
        {editing ? (
          <form
            className="flex items-center gap-2"
            onSubmit={(event) => {
              event.preventDefault();
              onUpdate(value);
              setEditing(false);
              setValue("");
            }}
          >
            <input
              aria-label={t("prices.newPrice")}
              inputMode="numeric"
              autoComplete="off"
              autoFocus
              value={value}
              onChange={(event) => {
                setValue(event.currentTarget.value);
              }}
              className="h-9 w-32 rounded-lg border border-border bg-surface px-3 text-sm text-text outline-none focus:border-accent"
            />
            <PrimaryButton type="submit" disabled={value.trim() === ""}>
              {t("prices.saveNew")}
            </PrimaryButton>
          </form>
        ) : (
          <SecondaryButton
            onClick={() => {
              setEditing(true);
            }}
          >
            {t("prices.updatePrice")}
          </SecondaryButton>
        )}
        <SecondaryButton onClick={onRemove}>{t("prices.remove")}</SecondaryButton>
      </span>
    </li>
  );
}
