"""Rule-based natural-language analytics engine (fully offline).

Understands Uzbek questions like "Jizzaxda bug'doy hosili nima uchun pasaydi?"
by extracting entities (region, crop, year) from the live database, detecting
the intent, running the relevant analytics and composing an evidence-backed
answer: yield dynamics, weather anomalies, irrigation deficit, price context
and a forecast where relevant.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

import pandas as pd

from analytics.timeseries import linear_forecast, percent_change
from database.engine import read_df

log = logging.getLogger(__name__)

INTENT_KEYWORDS: dict[str, list[str]] = {
    "why": ["nega", "nima uchun", "sabab", "pasaydi", "kamaydi", "tushdi"],
    "forecast": ["prognoz", "bashorat", "kelgusi", "keyingi yil", "qancha bo'ladi"],
    "price": ["narx", "narxi", "qancha turadi", "bozor"],
    "recommend": ["tavsiya", "qaysi ekin", "nima eksam", "eng foydali", "maslahat"],
    "weather": ["ob-havo", "harorat", "yog'in", "yomg'ir", "namlik", "iqlim"],
    "compare": ["solishtir", "taqqosla", "farqi", "qaysi yaxshi"],
    "finance": ["daromad", "foyda", "zarar", "roi", "xarajat", "kredit", "subsidiya"],
}


def _normalize(text: str) -> str:
    text = text.lower()
    for apostrophe in ("‘", "’", "ʻ", "ʼ", "`", "´"):
        text = text.replace(apostrophe, "'")
    return re.sub(r"\s+", " ", text).strip()


@dataclass
class QueryContext:
    """Entities extracted from a natural-language question."""

    intent: str = "stats"
    region: str | None = None
    region_id: int | None = None
    crop: str | None = None
    crop_id: int | None = None
    year: int | None = None
    matched: list[str] = field(default_factory=list)


class AIAssistant:
    """Offline NL query engine over the analytics database."""

    def parse(self, question: str) -> QueryContext:
        text = _normalize(question)
        context = QueryContext()

        for intent, keywords in INTENT_KEYWORDS.items():
            if any(keyword in text for keyword in keywords):
                context.intent = intent
                break

        regions = read_df("SELECT id, name FROM regions")
        for row in regions.itertuples():
            stem = _normalize(row.name)[:5]
            if stem in text:
                context.region, context.region_id = row.name, int(row.id)
                context.matched.append(row.name)
                break

        crops = read_df("SELECT id, name FROM crops")
        for row in crops.itertuples():
            stem = _normalize(row.name)[:5]
            if stem in text:
                context.crop, context.crop_id = row.name, int(row.id)
                context.matched.append(row.name)
                break

        year_match = re.search(r"(20\d{2})", text)
        if year_match:
            context.year = int(year_match.group(1))
        return context

    def ask(self, question: str) -> dict:
        """Answer a question; returns {'answer': str, 'table': DataFrame|None}."""
        try:
            context = self.parse(question)
            handler = {
                "why": self._answer_why,
                "forecast": self._answer_forecast,
                "price": self._answer_price,
                "recommend": self._answer_recommend,
                "weather": self._answer_weather,
                "compare": self._answer_compare,
                "finance": self._answer_finance,
                "stats": self._answer_stats,
            }[context.intent]
            return handler(context)
        except Exception:  # noqa: BLE001
            log.exception("AI so'rovi xatosi")
            return {"answer": "So'rovni tahlil qilishda xatolik yuz berdi. "
                              "Savolni boshqacha ifodalab ko'ring.", "table": None}

    # ------------------------------------------------------------------
    def _yield_series(self, context: QueryContext) -> pd.DataFrame:
        sql = (
            "SELECT y.year, ROUND(AVG(y.yield_t_ha),2) AS avg_yield,"
            " ROUND(SUM(y.production_t),0) AS production"
            " FROM yield_records y"
            " JOIN fields f ON f.id = y.field_id"
            " JOIN farms fa ON fa.id = f.farm_id"
            " JOIN districts d ON d.id = fa.district_id"
            " JOIN regions r ON r.id = d.region_id"
        )
        clauses, params = [], {}
        if context.region_id:
            clauses.append("r.id = :region_id")
            params["region_id"] = context.region_id
        if context.crop_id:
            clauses.append("y.crop_id = :crop_id")
            params["crop_id"] = context.crop_id
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " GROUP BY y.year ORDER BY y.year"
        return read_df(sql, params)

    def _scope_label(self, context: QueryContext) -> str:
        parts = []
        if context.region:
            parts.append(context.region)
        if context.crop:
            parts.append(context.crop.lower())
        return " — ".join(parts) if parts else "respublika bo'yicha"

    def _answer_why(self, context: QueryContext) -> dict:
        series = self._yield_series(context)
        if len(series) < 2:
            return {"answer": "Tahlil uchun yetarli tarixiy ma'lumot topilmadi.",
                    "table": series}
        target_year = context.year or int(series.iloc[-1]["year"])
        row = series[series.year == target_year]
        prev = series[series.year == target_year - 1]
        if row.empty or prev.empty:
            return {"answer": f"{target_year}-yil uchun ma'lumot topilmadi.",
                    "table": series}
        current = float(row.iloc[0]["avg_yield"])
        previous = float(prev.iloc[0]["avg_yield"])
        change = percent_change(previous, current)
        scope = self._scope_label(context)

        reasons: list[str] = []
        if context.region:
            from weather.service import season_summary

            this_season = season_summary(context.region, target_year)
            history = [season_summary(context.region, y)
                       for y in range(target_year - 4, target_year)]
            history = [h for h in history if h]
            if this_season and history:
                mean_precip = sum(h["precip"] for h in history) / len(history)
                precip_change = percent_change(mean_precip, this_season["precip"])
                if precip_change < -15:
                    reasons.append(
                        f"mavsumiy yog'ingarchilik o'rtachadan {abs(precip_change):.0f}% "
                        f"kam bo'ldi ({this_season['precip']:.0f} mm)")
                mean_temp = sum(h["t_avg"] for h in history) / len(history)
                if this_season["t_avg"] - mean_temp > 1:
                    reasons.append(
                        f"o'rtacha harorat {this_season['t_avg'] - mean_temp:.1f}°C yuqori bo'ldi")

            irrigation = read_df(
                "SELECT CAST(strftime('%Y', i.date) AS INTEGER) AS year,"
                " SUM(i.water_m3) AS water"
                " FROM irrigation_records i"
                " JOIN fields f ON f.id = i.field_id"
                " JOIN farms fa ON fa.id = f.farm_id"
                " JOIN districts d ON d.id = fa.district_id"
                " JOIN regions r ON r.id = d.region_id"
                " WHERE r.id = :rid GROUP BY year ORDER BY year",
                {"rid": context.region_id},
            )
            this_water = irrigation[irrigation.year == target_year]
            past_water = irrigation[irrigation.year < target_year]
            if not this_water.empty and not past_water.empty:
                water_change = percent_change(
                    float(past_water["water"].mean()), float(this_water.iloc[0]["water"]))
                if water_change < -10:
                    reasons.append(
                        f"sug'orish hajmi o'rtachadan {abs(water_change):.0f}% kamaydi")

        if change < 0:
            answer = (f"{scope.capitalize()}: {target_year}-yilda o'rtacha hosildorlik "
                      f"{previous:.2f} t/ga dan {current:.2f} t/ga ga tushdi "
                      f"({change:+.1f}%).\n\n")
            if reasons:
                answer += "Asosiy sabablar (ma'lumotlar tahlili):\n" + "\n".join(
                    f"• {reason};" for reason in reasons)
            else:
                answer += ("Ob-havo va sug'orish ko'rsatkichlarida keskin og'ish "
                           "aniqlanmadi — pasayish agrotexnika yoki navlar bilan "
                           "bog'liq bo'lishi mumkin.")
        else:
            answer = (f"{scope.capitalize()}: {target_year}-yilda hosildorlik aslida "
                      f"pasaymagan — {previous:.2f} dan {current:.2f} t/ga ga "
                      f"o'zgardi ({change:+.1f}%).")
        return {"answer": answer, "table": series}

    def _answer_forecast(self, context: QueryContext) -> dict:
        series = self._yield_series(context)
        if len(series) < 3:
            return {"answer": "Prognoz uchun kamida 3 yillik ma'lumot kerak.",
                    "table": series}
        values = series["avg_yield"].tolist()
        forecast, lower, upper = linear_forecast(values, periods=1)
        next_year = int(series.iloc[-1]["year"]) + 1
        answer = (
            f"{self._scope_label(context).capitalize()} uchun {next_year}-yil prognozi: "
            f"o'rtacha hosildorlik ≈ {forecast[0]:.2f} t/ga "
            f"(ishonch oralig'i: {lower[0]:.2f} – {upper[0]:.2f} t/ga).\n"
            f"So'nggi 5 yil trendi: {values[0]:.2f} → {values[-1]:.2f} t/ga."
        )
        return {"answer": answer, "table": series}

    def _answer_price(self, context: QueryContext) -> dict:
        if not context.crop_id:
            from market.service import latest_prices

            table = latest_prices()
            return {"answer": "Barcha ekinlar bo'yicha so'nggi bozor narxlari quyida.",
                    "table": table}
        prices = read_df(
            "SELECT date, price_per_kg FROM market_prices"
            " WHERE crop_id = :c ORDER BY date DESC LIMIT 52", {"c": context.crop_id},
        ).sort_values("date")
        latest = float(prices.iloc[-1]["price_per_kg"])
        mean = float(prices["price_per_kg"].mean())
        forecast, lower, upper = linear_forecast(prices["price_per_kg"].tolist(), 4)
        answer = (
            f"{context.crop}: joriy narx {latest:,.0f} so'm/kg "
            f"(yillik o'rtacha {mean:,.0f} so'm/kg).\n"
            f"1 oylik prognoz: {forecast[-1]:,.0f} so'm/kg atrofida "
            f"({lower[-1]:,.0f} – {upper[-1]:,.0f})."
        )
        return {"answer": answer, "table": prices.tail(10)}

    def _answer_recommend(self, context: QueryContext) -> dict:
        from ml.service import recommend_crops
        from weather.service import season_summary

        region = context.region or "Toshkent"
        region_row = read_df(
            "SELECT id, fertility FROM regions WHERE name = :n", {"n": region})
        if region_row.empty:
            return {"answer": "Viloyat topilmadi — savolda viloyat nomini keltiring.",
                    "table": None}
        from analytics.kpi import latest_year

        season = season_summary(region, latest_year()) or {"precip": 150, "t_avg": 24}
        recommendations = recommend_crops(
            int(region_row.iloc[0]["id"]), season["precip"], season["t_avg"],
            float(region_row.iloc[0]["fertility"]))
        lines = "\n".join(
            f"{i + 1}. {rec['crop']} (model ishonchi: {rec['confidence']}%)"
            for i, rec in enumerate(recommendations))
        answer = (f"{region} viloyati uchun ML modeli tavsiya qilgan eng foydali "
                  f"ekinlar (tarixiy foyda va iqlim asosida):\n{lines}")
        return {"answer": answer, "table": pd.DataFrame(recommendations)}

    def _answer_weather(self, context: QueryContext) -> dict:
        from analytics.kpi import latest_year

        region = context.region or "Toshkent"
        year = context.year or latest_year()
        from weather.service import season_summary

        season = season_summary(region, year)
        if season is None:
            return {"answer": f"{region} bo'yicha {year}-yil ob-havo ma'lumoti topilmadi.",
                    "table": None}
        answer = (
            f"{region} viloyati, {year}-yil vegetatsiya mavsumi (aprel–sentabr):\n"
            f"• Yog'ingarchilik: {season['precip']:.0f} mm\n"
            f"• O'rtacha harorat: {season['t_avg']:.1f}°C\n"
            f"• O'rtacha namlik: {season['humidity']:.0f}%"
        )
        return {"answer": answer, "table": None}

    def _answer_compare(self, context: QueryContext) -> dict:
        from analytics.kpi import latest_year, yield_by_region

        table = yield_by_region(context.year or latest_year())
        best, worst = table.iloc[0], table.iloc[-1]
        answer = (
            f"{context.year or latest_year()}-yil viloyatlar taqqoslamasi:\n"
            f"• Eng yuqori ishlab chiqarish: {best.region} ({best.production:,.0f} t)\n"
            f"• Eng past: {worst.region} ({worst.production:,.0f} t)\n"
            f"To'liq jadval quyida."
        )
        return {"answer": answer, "table": table}

    def _answer_finance(self, context: QueryContext) -> dict:
        from analytics.kpi import latest_year
        from finance.service import yearly_summary

        table = yearly_summary()
        year = context.year or latest_year()
        row = table[table.year == year]
        if row.empty:
            return {"answer": f"{year}-yil moliya ma'lumotlari topilmadi.", "table": table}
        record = row.iloc[0]
        answer = (
            f"{year}-yil moliyaviy natijalar (platforma bo'yicha):\n"
            f"• Daromad: {record.income / 1e9:,.1f} mlrd so'm\n"
            f"• Xarajat: {record.expense / 1e9:,.1f} mlrd so'm\n"
            f"• Sof foyda: {record.profit / 1e9:,.1f} mlrd so'm (ROI: {record.roi}%)\n"
            f"• Kreditlar: {record.credit / 1e9:,.1f} mlrd, subsidiyalar: "
            f"{record.subsidy / 1e9:,.1f} mlrd so'm"
        )
        return {"answer": answer, "table": table}

    def _answer_stats(self, context: QueryContext) -> dict:
        from analytics.kpi import compute_kpi

        kpi = compute_kpi(context.year)
        series = self._yield_series(context)
        scope = self._scope_label(context)
        extra = ""
        if not series.empty and (context.region or context.crop):
            last = series.iloc[-1]
            extra = (f"\n{scope.capitalize()}: {int(last.year)}-yilda o'rtacha "
                     f"hosildorlik {last.avg_yield} t/ga, ishlab chiqarish "
                     f"{last.production:,.0f} t.")
        answer = (
            f"{kpi.year}-yil umumiy ko'rsatkichlari:\n"
            f"• Yer maydoni: {kpi.total_area_ha:,.0f} ga | Fermerlar: {kpi.farmers} | "
            f"Xo'jaliklar: {kpi.farms} | Dalalar: {kpi.fields}\n"
            f"• O'rtacha hosildorlik: {kpi.avg_yield_t_ha} t/ga, jami "
            f"{kpi.production_t:,.0f} t mahsulot\n"
            f"• Moliyaviy natija: foyda {kpi.profit / 1e9:,.1f} mlrd so'm "
            f"(ROI {kpi.roi_percent}%)\n"
            f"• O'rtacha NDVI (so'nggi 60 kun): {kpi.avg_ndvi}" + extra
        )
        return {"answer": answer, "table": series if not series.empty else None}


assistant = AIAssistant()
