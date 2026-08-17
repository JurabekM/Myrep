"""Kategoriyalash modeli uchun urug' (seed) o'quv to'plami.

Har bir yozuv - foydalanuvchi kiritishi mumkin bo'lgan qisqa tranzaksiya matni
(o'zbek/rus tilida, chek/ovozli kiritish uslubida). Production'da bu to'plam
haqiqiy foydalanuvchi tranzaksiyalari bilan to'ldiriladi va model qayta o'qitiladi
(`app/training/train_classifier.py`).
"""

CATEGORY_SAMPLES: dict[str, list[str]] = {
    "food": [
        "oziq ovqat", "bozor", "sabzavot meva", "non sut", "korzinka", "makro",
        "produkty", "eda", "rынок", "gasht", "guruch yogʻ",
    ],
    "transport": [
        "taksi", "avtobus", "metro", "yandex taxi", "bolt", "marshrutka",
        "transport", "taxi", "avtobus chiptasi", "metro karta",
    ],
    "shopping": [
        "kiyim", "poyabzal", "market", "do'kon", "sotib oldim", "pokupka",
        "magazin", "shopping", "elektronika", "aksessuar",
    ],
    "restaurant": [
        "restoran", "kafe", "fastfud", "pitsa", "burger", "restaurant",
        "kofexona", "kafe uchun", "ovqatlandim",
    ],
    "entertainment": [
        "kino", "konsert", "o'yin", "developer", "netflix", "steam",
        "razvlecheniya", "kinoteatr", "bilyard", "bowling",
    ],
    "medical": [
        "dorixona", "shifokor", "klinika", "tibbiyot", "analiz", "vrach",
        "apteka", "stomatolog", "kasalxona",
    ],
    "education": [
        "kurs", "repetitor", "universitet", "kitob", "ta'lim", "kurslar",
        "maktab to'lovi", "til kursi", "trening",
    ],
    "travel": [
        "aviachipta", "mehmonxona", "sayohat", "otel", "poyezd chiptasi",
        "puteshestvie", "turizm", "viza",
    ],
    "utilities": [
        "kommunal", "svet", "gaz", "suv haqi", "elektr energiya",
        "kommunalnye uslugi", "isitish",
    ],
    "subscriptions": [
        "obuna", "podписка", "spotify", "youtube premium", "oylik obuna",
        "ilova obunasi",
    ],
    "fuel": [
        "benzin", "yoqilg'i", "az stansiya", "zapravka", "dizel", "metan",
        "moy almashtirish",
    ],
    "internet": [
        "internet", "wifi", "mobil aloqa", "simkarta", "beeline", "ucell",
        "uztelecom", "internet to'lovi",
    ],
    "other": [
        "boshqa", "turli xarajat", "sovg'a berdim", "noma'lum", "prochee",
        "xizmat haqi",
    ],
}
