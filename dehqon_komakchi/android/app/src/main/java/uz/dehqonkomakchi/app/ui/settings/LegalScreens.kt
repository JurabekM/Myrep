package uz.dehqonkomakchi.app.ui.settings

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun PrivacyPolicyScreen() {
    LegalTextScreen(
        title = "Maxfiylik siyosati",
        body = PRIVACY_POLICY_UZ,
    )
}

@Composable
fun TermsScreen() {
    LegalTextScreen(
        title = "Foydalanish shartlari",
        body = TERMS_OF_USE_UZ,
    )
}

@Composable
private fun LegalTextScreen(title: String, body: String) {
    Scaffold { padding ->
        Column(
            modifier = Modifier
                .padding(padding)
                .padding(16.dp)
                .verticalScroll(rememberScrollState()),
        ) {
            Text(title, style = MaterialTheme.typography.headlineMedium)
            Text(body, style = MaterialTheme.typography.bodyLarge, modifier = Modifier.padding(top = 16.dp))
        }
    }
}

private const val PRIVACY_POLICY_UZ = """
So'nggi yangilanish: 2026-yil

Dehqon Ko'makchi ilovasi sizning maxfiyligingizni hurmat qiladi. Ushbu hujjat qanday ma'lumotlar yig'ilishini va ulardan qanday foydalanilishini tushuntiradi.

1. Qanday ma'lumotlar yig'iladi
- Siz kiritgan ma'lumotlar: viloyat/tuman, ekish sanasi, xarajat/hosil/sotuv yozuvlari, bozor e'lonlari.
- Surat: tekshirish uchun yuklangan barg/meva suratlari faqat qurilmangizda saqlanadi, agar siz backend bilan sinxronlashni yoqmasangiz.
- Joylashuv: faqat aniq ruxsat bergan holingizda va faqat ob-havo/sug'orish tavsiyalari uchun ishlatiladi.
- Telefon raqami: faqat siz roziligingizni bildirgan holda bozor e'lonida ko'rsatiladi yoki OTP orqali autentifikatsiya uchun ishlatiladi.

2. Ma'lumotlar qanday saqlanadi
Ma'lumotlarning katta qismi qurilmangizda (mahalliy bazada) saqlanadi. Agar kelajakda bulutli sinxronizatsiya yoqilsa, bu haqda alohida xabar beriladi va rozilik so'raladi.

3. Ma'lumotlarni kimlar bilan bo'lishamiz
Sizning roziligingizsiz uchinchi shaxslarga shaxsiy ma'lumotlar berilmaydi. Bozor bo'limida faqat siz aniq rozilik bildirgan kontakt ma'lumoti boshqa foydalanuvchilarga ko'rinadi.

4. Ma'lumotlarni o'chirish
Sozlamalar bo'limidan "Ma'lumotlarni o'chirish" tugmasi orqali barcha mahalliy ma'lumotlaringizni butunlay o'chirishingiz mumkin.

5. Bog'lanish
Savollar bo'yicha ilova ishlab chiqaruvchisiga murojaat qiling.
"""

private const val TERMS_OF_USE_UZ = """
So'nggi yangilanish: 2026-yil

1. Xizmat tavsifi
Dehqon Ko'makchi — kichik fermerlar va bog'dorlar uchun yordamchi ilova. Tekshirish (diagnostika) natijalari umumiy yo'nalish sifatida beriladi va professional agronom xulosasini almashtirmaydi.

2. Javobgarlikni cheklash
Ilova tomonidan berilgan tavsiyalar (kasallik tekshiruvi, sug'orish maslahati) faqat umumiy ma'lumot xarakteriga ega. Muhim qarorlar (kimyoviy vositalardan foydalanish, katta hajmdagi sarmoya) oldidan mutaxassis bilan maslahatlashish tavsiya etiladi.

3. Foydalanuvchi majburiyatlari
- Bozor bo'limida faqat haqiqiy va aniq ma'lumot joylashtiring.
- Spam, firibgarlik yoki nomaqbul kontent joylashtirish taqiqlanadi va shikoyat asosida o'chirilishi mumkin.

4. Kontent moderatsiyasi
Bir nechta shikoyat tushgan e'lonlar avtomatik ravishda vaqtincha yashiriladi va ko'rib chiqiladi.

5. O'zgarishlar
Ushbu shartlar vaqti-vaqti bilan yangilanishi mumkin.
"""
