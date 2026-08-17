"""Dashboard uchun ma'lumot to'plash (usage, biznes salomatligi)."""

from __future__ import annotations

from app.core.config import BusinessProfile
from app.data.repositories.kb_repo import UsageRepository


class DashboardService:
    def __init__(self, usage: UsageRepository, profile: BusinessProfile):
        self._usage = usage
        self._profile = profile

    def usage_by_day(self, days: int = 30) -> list[dict]:
        return self._usage.by_day(days)

    def usage_by_module(self) -> list[dict]:
        return self._usage.by_module()

    def usage_by_provider(self) -> list[dict]:
        return self._usage.by_provider()

    def business_health(self) -> dict:
        """Profil to'liqligi + faollik asosidagi tarkibiy ball (0-100)."""
        p = self._profile
        fields = [p.industry, p.business_type, p.location, p.employees, p.goals]
        profile_score = sum(1 for f in fields if f) / len(fields)

        active_days = len(self._usage.by_day(30))
        engagement = min(active_days / 20, 1.0)

        score = round((profile_score * 0.4 + engagement * 0.6) * 100)
        recommendations: list[str] = []
        if profile_score < 1:
            recommendations.append(
                "Biznes profilingizni to'ldiring — AI maslahatlar aniqroq bo'ladi"
            )
        if active_days < 5:
            recommendations.append(
                "Platformadan muntazam foydalaning: haftalik reja va KPI so'rang"
            )
        return {
            "score": score,
            "profile_completeness": round(profile_score * 100),
            "engagement": round(engagement * 100),
            "recommendations": recommendations,
        }
