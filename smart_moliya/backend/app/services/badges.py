"""Badge katalogi - statik, kod ichida. Yangi badge qo'shish uchun shu ro'yxatga
kiritish va uni qaerdadir `GamificationService.award_badge` orqali chaqirish yetarli.
"""

BADGE_CATALOG: dict[str, dict] = {
    "first_transaction": {
        "name": "Birinchi qadam",
        "description": "Birinchi tranzaksiyangizni qo'shdingiz",
        "xp_reward": 50,
    },
    "streak_7_days": {
        "name": "Bir hafta izchil",
        "description": "7 kun ketma-ket ilovadan foydalandingiz",
        "xp_reward": 150,
    },
    "streak_30_days": {
        "name": "Oylik marafon",
        "description": "30 kun ketma-ket ilovadan foydalandingiz",
        "xp_reward": 500,
    },
    "first_goal_completed": {
        "name": "Maqsadga erishdingiz",
        "description": "Birinchi jamg'arma maqsadingizni yakunladingiz",
        "xp_reward": 300,
    },
    "first_budget_created": {
        "name": "Rejalashtiruvchi",
        "description": "Birinchi byudjetingizni yaratdingiz",
        "xp_reward": 50,
    },
    "challenge_completed": {
        "name": "Challenge g'olibi",
        "description": "Bir challenge'ni muvaffaqiyatli yakunladingiz",
        "xp_reward": 200,
    },
}
