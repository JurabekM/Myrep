import { type SyntheticEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { type PyramidDto, commands } from "../../bindings/bindings";
import { unwrap } from "../finance/command-error";
import { useErrorMessage } from "../finance/errors";
import { Alert, Card, Field, PrimaryButton, Stat } from "../finance/ui";

/**
 * Piramida — ta'limiy hisob (SPEC 2G.4): har ishtirokchi `k` odam olib keladi, aholi tugaganda cho'kadi.
 * «Cho'kkan kuni siz qaysi qavatda bo'lasiz?» Hisob Rustda, saqlanmaydi.
 */
export function PyramidCard() {
  const { t } = useTranslation();
  const message = useErrorMessage();
  const [recruits, setRecruits] = useState("5");
  const [population, setPopulation] = useState("1000000");
  const [model, setModel] = useState<PyramidDto | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function calculate(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      setModel(unwrap(await commands.pyramidModel(Number(recruits), Number(population))));
    } catch (caught) {
      setError(message(caught));
    }
  }

  return (
    <Card title={t("pyramid.title")}>
      <p className="text-sm text-muted">{t("pyramid.intro")}</p>
      <form
        className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3"
        onSubmit={(event) => void calculate(event)}
      >
        <Field
          id="pyramid-k"
          label={t("pyramid.recruits")}
          type="number"
          min={2}
          value={recruits}
          onChange={(event) => {
            setRecruits(event.currentTarget.value);
          }}
        />
        <Field
          id="pyramid-n"
          label={t("pyramid.population")}
          type="number"
          min={1}
          value={population}
          onChange={(event) => {
            setPopulation(event.currentTarget.value);
          }}
        />
        <div className="flex items-end">
          <PrimaryButton type="submit" disabled={Number(recruits) < 2 || Number(population) < 1}>
            {t("pyramid.calculate")}
          </PrimaryButton>
        </div>
      </form>
      {model !== null ? (
        <div className="flex flex-col gap-3" role="status">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <Stat label={t("pyramid.levels")} value={String(model.levels)} />
            <Stat
              label={t("pyramid.lastLevel")}
              value={model.lastLevel.toLocaleString("uz-UZ")}
              hint={
                model.lastLevelFull ? t("pyramid.lastLevelFull") : t("pyramid.lastLevelPartial")
              }
            />
            <Stat
              label={t("pyramid.lastShare")}
              value={t("pyramid.percent", { value: (model.lastLevelShareBp / 100).toFixed(1) })}
            />
          </div>
          <p className="text-sm text-text">{t("pyramid.question")}</p>
          <p className="text-xs text-subtle">{t("pyramid.bait")}</p>
        </div>
      ) : null}
      {error !== null ? <Alert>{error}</Alert> : null}
    </Card>
  );
}
