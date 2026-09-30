"""Qanday ishlaydi — oddiy tilda."""

from __future__ import annotations

from app.vidjetlar import Karta, Sahifa, yorliq

MATN = [
    ("Zarbxona nima qiladi?",
     "Zarbxona raqamli pulni — kupyuralarni — «zarb qiladi», ya'ni yaratadi va imzolaydi. "
     "U bankning kalitini hech qachon olmaydi. Bank unga <b>sertifikat</b> beradi: «shu "
     "kalitga, shuncha limit, shu muddatgacha». Zarbxona pulni shu vakolat doirasida "
     "chiqaradi, bank esa hamma narsani qaytadan tekshiradi va qabul qiladi yoki rad etadi."),
    ("Kupyura",
     "Har kupyura qog'oz pulga o'xshaydi. <b>Ochiq sarlavha</b> (raqam, nominal, egasi, tartib "
     "raqami) hamma uchun ko'rinadi. <b>Muhrlangan yadro</b> ichida kupyuraning «mikrochipi» — "
     "nazorat kaliti turadi: kimda shu kalit bo'lsa, kupyura o'shaniki. Muhr sarlavhaga "
     "bog'langan: nominal yoki egasi o'zgartirilsa, muhr ochilmaydi."),
    ("Partiya va Merkle daraxti",
     "Kupyuralar partiyalarga yig'iladi. Hamma kupyuradan bitta <b>Merkle ildizi</b> "
     "hisoblanadi va zarbxona uni o'z ML-DSA-65 kaliti bilan imzolaydi. Bitta imzo butun "
     "partiyani himoyalaydi: bironta kupyura o'zgarsa, ildiz boshqacha chiqadi."),
    ("Nega sekin?",
     "Zarb juda tez bo'lishi mumkin: 100 000 kupyura bir necha soniyada tayyor. Lekin unda "
     "protsessor to'la band bo'ladi va operator jarayonni ko'rmaydi. Shuning uchun konveyer "
     "<b>sekin, kam resurs bilan va jonli monitor ostida</b> ishlaydi. Tezlik (kupyura/s), "
     "davomiylik yoki protsessor byudjetini tanlang. Sovutish tanaffuslari ham bor. Sur'at "
     "natijani o'zgartirmaydi: sekin va tez zarb bayt-ma-bayt bir xil."),
    ("Buyurtma va uzilish",
     "Katta summa kichik partiyalarga bo'linadi. Har partiya yopilishi bilan imzolanadi, "
     "tekshiriladi, faylga yoziladi va jurnalga tushadi. Partiyaning maxfiy kalitlari hech "
     "qachon diskka yozilmaydi. Shuning uchun dastur uzilib qolsa, faqat <b>joriy</b> partiya "
     "yo'qoladi: u hali imzolanmagan va hech qayerda mavjud emas. Buyurtma keyingi "
     "kupyuradan davom etadi."),
    ("Tekshiruv",
     "Faylga yozishdan oldin har partiya noldan qayta hisoblanadi. Bu bankning qabul "
     "qoidalarini takrorlaydi. «Tekshiruv» sahifasida istalgan faylni yoki butun jurnalni "
     "tekshirish mumkin. Buzib ko'rish demosi tekshiruv haqiqatan ishlashini ko'rsatadi. "
     "«Tekshirilmadi» hech qachon «toza» deb ko'rsatilmaydi. Jurnal yozuvlari xesh-zanjir "
     "bilan bog'langan va zanjir boshi zarbxona kaliti bilan imzolangan. Shuning uchun "
     "jurnaldan yozuvni sezdirmay o'chirib yoki o'zgartirib bo'lmaydi."),
    ("Bankka topshirish",
     "Ikki yo'l bor. <b>Fayl orqali</b>: .aqbatch faylini bankka bering, keyin «Topshirildi "
     "deb belgilash» ni bosing. <b>Onlayn</b>: MQTT broker ustida AETHER-Q post-kvant "
     "sessiyasi orqali yuboriladi. Bank kaliti sertifikatdan olinadi va pinlanadi. Broker "
     "paketlarni ko'radi, lekin o'qiy olmaydi va o'zgartira olmaydi. Onlayn topshirish uchun "
     "<code>aetherq_core</code> kutubxonasi kerak."),
]


class QandaySahifasi(Sahifa):
    sarlavha_matni = "Qanday ishlaydi"

    def __init__(self, ctx):
        super().__init__(ctx)
        for sarlavha, matn in MATN:
            k = Karta(sarlavha)
            k.qosh(yorliq(matn))
            self.qosh(k)
        self.oxiri()
