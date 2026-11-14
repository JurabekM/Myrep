import 'package:flutter/material.dart';

import '../core/risk.dart';
import 'quiz_screen.dart';
import 'report_screen.dart';
import 'theme.dart';
import 'widgets.dart';

/// Firibgarlik turlari (ROSTOR-1 tahdid modeli T1–T6 + T7) va shoshilinch yo'riqnoma.
class LearnScreen extends StatelessWidget {
  const LearnScreen({super.key});

  static const _threats = [
    (Icons.android_rounded, "Telegram'da kelgan .apk fayl",
        "Tanishingiz nomidan \"soliq.apk\", \"rasm.apk\" yoki \"bank yangilanishi\" keladi. O'rnatilgach SMS kodlarni o'g'irlaydi va o'zini kontaktlaringizga tarqatadi.",
        "Hech qachon xabar orqali kelgan faylni o'rnatmang. ROSTOR-2 bilan oching yoki o'chiring."),
    (Icons.phone_in_talk_rounded, "\"Bank xavfsizlik xizmati\" qo'ng'irog'i",
        "\"Kartangizda shubhali operatsiya, bekor qilish uchun SMS kodni ayting\" deyishadi. Aslida kod ularning o'zi boshlagan o'tkazmani tasdiqlaydi.",
        "Go'shakni qo'ying. Bankka kartaning orqasidagi raqam orqali o'zingiz qo'ng'iroq qiling."),
    (Icons.gavel_rounded, "Militsiya, sud yoki soliq nomidan qo'rqitish",
        "\"Sizga qarshi jinoiy ish ochildi\", \"jarima to'lanmasa hibsga olinasiz\" — shoshilinch to'lov yoki ma'lumot talab qilinadi.",
        "Rasmiy idoralar telefon yoki Telegram orqali pul talab qilmaydi. 102 ga o'zingiz qo'ng'iroq qilib tekshiring."),
    (Icons.sim_card_rounded, "SIM-kartani almashtirish (SIM swap)",
        "Firibgar raqamingizni o'z SIM-kartasiga ko'chiradi va SMS orqali bank, Telegram akkauntlaringizni tiklab oladi.",
        "Telegram'da ikki bosqichli parolni yoqing. Telefon to'satdan tarmoqdan chiqsa, darhol operatorga murojaat qiling."),
    (Icons.storefront_rounded, "OLX va bozordagi \"xaridor\"",
        "\"Pulni o'tkazdim, olish uchun havolaga kirib karta ma'lumotini kiriting\" deyishadi. Havola kartadan pul YECHADI.",
        "Pul olish uchun faqat karta raqami kerak. Muddat, CVV yoki SMS kod hech qachon kerak emas."),
    (Icons.trending_up_rounded, "Oson daromad va investitsiya",
        "\"Kuniga 100\$\", \"kafolatlangan foyda\", \"uydan ish, faqat ro'yxatdan o'tish puli\" va'da qilinadi.",
        "Kafolatlangan yuqori daromad bo'lmaydi. Oldindan to'lov so'ralsa — bu firibgarlik."),
    (Icons.how_to_vote_rounded, "\"Ovoz bering\" va Telegram akkaunti",
        "Tanishingizdan \"qizimga ovoz bering\" havolasi keladi. Bot telefon raqami va Telegram kodini so'raydi — akkaunt firibgarga o'tadi.",
        "Telegram kirish kodini hech qayerga kiritmang. Kodni so'ragan har qanday sayt yoki bot — firibgar."),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Firibgarlik turlari')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
        children: [
          const VerdictBanner(
            severity: Severity.info,
            title: 'Asosiy qoida',
            subtitle: "SMS kod, karta muddati va CVV faqat sizniki. Ularni so'ragan har qanday odam — xodim, militsioner yoki tanish bo'lsa ham — firibgar.",
          ),
          const SectionTitle('Eng ko\'p uchraydigan usullar'),
          for (final t in _threats)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Card(child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(children: [
                    Icon(t.$1, color: RColors.accent),
                    const SizedBox(width: 10),
                    Expanded(child: Text(t.$2, style: Theme.of(context).textTheme.titleMedium)),
                  ]),
                  const SizedBox(height: 8),
                  Text(t.$3),
                  const SizedBox(height: 8),
                  Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Icon(Icons.check_circle_rounded, size: 18, color: RColors.of(Severity.ok)),
                    const SizedBox(width: 8),
                    Expanded(child: Text(t.$4, style: TextStyle(color: RColors.of(Severity.ok), fontWeight: FontWeight.w600))),
                  ]),
                ]),
              )),
            ),
          const SectionTitle("Hech kim majburlay olmaydi"),
          const Card(child: Padding(
            padding: EdgeInsets.all(16),
            child: Text(
              "Hech kim — hatto forma kiygan odam ham — sizni ko'chada QR kod yoki fayl orqali ilova o'rnatishga majburlay olmaydi. "
              "Firibgarlar aynan shu ishonchdan foydalanadi. Ilovani o'zingiz, Google Play'dan, o'zingiz tanlab o'rnating.",
            ),
          )),
          const SectionTitle('Pul yechilgan bo\'lsa — darhol'),
          const Card(child: Padding(
            padding: EdgeInsets.all(16),
            child: Text(
              "1. Bank ilovasida kartani bloklang yoki kartaning orqasidagi raqamga qo'ng'iroq qiling.\n"
              "2. Firibgarga ko'rsatgan barcha kod va parollarni almashtiring.\n"
              "3. 102 ga murojaat qiling. Xabarlar, qo'ng'iroq vaqti va o'tkazma ma'lumotlarini saqlab qo'ying — "
              "ROSTOR-2 ularni imzolangan hisobotga yig'ib beradi.\n"
              "4. Telegram akkaunti o'g'irlangan bo'lsa, tanishlaringizni darhol ogohlantiring.",
            ),
          )),
          const SizedBox(height: 10),
          OutlinedButton.icon(
            onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const ReportsScreen())),
            icon: const Icon(Icons.description_rounded),
            label: const Text('Hisobot yaratish'),
          ),
          const SizedBox(height: 18),
          FilledButton.icon(
            onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const QuizScreen())),
            icon: const Icon(Icons.quiz_rounded),
            label: const Text("O'zingizni sinang: 9 ta vaziyat"),
          ),
        ],
      ),
    );
  }
}
