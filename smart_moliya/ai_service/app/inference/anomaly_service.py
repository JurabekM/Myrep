import statistics


class AnomalyService:
    """Z-score asosidagi anomaliya aniqlash - kategoriya bo'yicha o'rtacha xarajatdan
    keskin chetlanishlarni (ehtimoliy noto'g'ri/firibgar tranzaksiya) belgilaydi.
    """

    Z_SCORE_THRESHOLD = 2.5

    def detect(self, amount: float, category_history: list[float]) -> dict:
        if len(category_history) < 3:
            return {"is_anomaly": False, "z_score": 0.0, "reason": "Tarix yetarli emas"}

        mean = statistics.mean(category_history)
        stdev = statistics.pstdev(category_history)

        if stdev == 0:
            is_anomaly = amount != mean
            return {
                "is_anomaly": is_anomaly,
                "z_score": 0.0,
                "reason": "Doimiy summadan chetlanish" if is_anomaly else "Normal",
            }

        z_score = (amount - mean) / stdev
        is_anomaly = abs(z_score) > self.Z_SCORE_THRESHOLD

        reason = (
            f"Bu kategoriyadagi o'rtacha xarajatdan {abs(z_score):.1f} marta standart chetlanish"
            if is_anomaly
            else "Normal"
        )
        return {"is_anomaly": is_anomaly, "z_score": round(z_score, 2), "reason": reason}


_anomaly_service: AnomalyService | None = None


def get_anomaly_service() -> AnomalyService:
    global _anomaly_service
    if _anomaly_service is None:
        _anomaly_service = AnomalyService()
    return _anomaly_service
