import 'package:flutter/material.dart';

import '../core/risk.dart';
import 'theme.dart';

/// F3 ta'lim bloki: haqiqiy firibgarlik vaziyatlari bo'yicha qisqa test.
/// Har javobdan keyin nima uchun to'g'ri yoki noto'g'ri ekani tushuntiriladi.
class QuizQuestion {
  const QuizQuestion(this.situation, this.options, this.correct, this.why);
  final String situation;
  final List<String> options;
  final int correct;
  final String why;
}

const quizQuestions = [
  QuizQuestion(
    "\"Bank xavfsizlik xizmati\"dan qo'ng'iroq: \"Kartangizdan shubhali to'lov ketyapti. Bekor qilish uchun hozir kelgan SMS kodni ayting.\"",
    ["Kodni aytaman — to'lovni to'xtatish kerak", "Go'shakni qo'yaman va bankka kartaning orqasidagi raqam orqali o'zim qo'ng'iroq qilaman"],
    1,
    "SMS kod to'lovni bekor qilmaydi — u firibgar boshlagan o'tkazmani tasdiqlaydi. Bank xodimi hech qachon kod so'ramaydi.",
  ),
  QuizQuestion(
    "OLX'da telefoningizni sotyapsiz. \"Xaridor\": \"Pulni o'tkazdim, olish uchun havolaga kirib karta muddati va CVV ni kiriting.\"",
    ["Havolaga kirib ma'lumotni kiritaman", "Rad etaman: pul olish uchun faqat karta raqami yetarli"],
    1,
    "Pul QABUL qilish uchun muddat, CVV yoki SMS kod hech qachon kerak emas. Bunday havola kartadan pul yechadi.",
  ),
  QuizQuestion(
    "Telegram'da tanishingizdan \"rasmlar.apk\" fayli keldi: \"Ko'r, bu sensan-ku!\"",
    ["Ochib ko'raman — tanishim yubordi", "O'rnatmayman, tanishimga telefon qilib so'rayman yoki ROSTOR-2 bilan tekshiraman"],
    1,
    "Bu klassik T1 hujumi: tanishingizning akkaunti allaqachon buzilgan. Rasm .apk bo'lmaydi; o'rnatilgan dastur SMS kodlaringizni o'g'irlaydi.",
  ),
  QuizQuestion(
    "Ekranda Click'ning rasmiy raqami ko'rinyapti. Qo'ng'iroq qilgan odam kartangiz muddatini so'rayapti.",
    ["Raqam rasmiy — demak ishonsa bo'ladi", "Raqamni soxtalashtirish mumkin — hech qanday ma'lumot bermayman"],
    1,
    "Firibgarlar ekranda istalgan raqamni ko'rsata oladi. Rasmiy raqamdan qo'ng'iroq bo'lsa ham, karta ma'lumoti so'ralsa — firibgarlik.",
  ),
  QuizQuestion(
    "Qarindoshingizdan xabar: \"Qizimga tanlovda ovoz bering\" va havola. Sayt telefon raqamingiz va Telegram'dan kelgan kodni so'raydi.",
    ["Kodni kiritaman — bu oddiy tasdiqlash", "Kiritmayman: bu kod Telegram akkauntimni boshqa telefonga ochadi"],
    1,
    "Telegram kirish kodi faqat Telegram ilovasining o'zida kerak. Uni so'ragan har qanday sayt yoki bot akkauntingizni egallaydi (T7).",
  ),
  QuizQuestion(
    "\"Militsiya\" xodimi: \"Sizning nomingizga jinoiy ish ochildi. Yopish uchun bugun shu kartaga jarima to'lang.\"",
    ["Qo'rqib, to'layman", "To'lamayman va 102 ga o'zim qo'ng'iroq qilib tekshiraman"],
    1,
    "Rasmiy idoralar telefon yoki Telegram orqali shaxsiy kartaga to'lov talab qilmaydi. Qo'rqitish — firibgarning asosiy quroli (T3).",
  ),
  QuizQuestion(
    "O'zingiz Payme'da to'lov qildingiz va SMS keldi: \"Tasdiqlash kodi 482913. Kodni hech kimga aytmang.\"",
    ["Bu oddiy bank SMS'i — kodni faqat o'z to'lovimga kiritaman", "Bu firibgarlik — darhol bankka qo'ng'iroq qilaman"],
    0,
    "To'lovni o'zingiz boshlagan bo'lsangiz, bu haqiqiy SMS. Xavf faqat shu kodni boshqa birov so'raganda paydo bo'ladi.",
  ),
  QuizQuestion(
    "Reklama: \"Uydan ishlab kuniga 100\$ daromad! Faqat 200 000 so'm ro'yxatdan o'tish puli.\"",
    ["Sinab ko'raman, summa kichik", "Bu firibgarlik: kafolatlangan daromad va oldindan to'lov — ikki belgi"],
    1,
    "Haqiqiy ish beruvchi sizdan pul so'ramaydi. \"Ro'yxatdan o'tish puli\" to'langach, keyingi \"soliq\", \"komissiya\" so'raladi (T6).",
  ),
  QuizQuestion(
    "Telefoningiz to'satdan \"Faqat favqulodda qo'ng'iroqlar\" deb ko'rsatyapti, keyin Telegram'dan \"yangi qurilmadan kirildi\" xabari keldi.",
    ["Telefonni o'chirib-yoqaman, o'tib ketadi", "Darhol operatorga murojaat qilaman — SIM-kartam boshqa joyda qayta chiqarilgan bo'lishi mumkin"],
    1,
    "Bu SIM swap belgisi (T4). Firibgar raqamingiz orqali bank va Telegram'ni tiklaydi. Har daqiqa muhim; Telegram'da ikki bosqichli parolni oldindan yoqing.",
  ),
];

class QuizScreen extends StatefulWidget {
  const QuizScreen({super.key});
  @override
  State<QuizScreen> createState() => _QuizScreenState();
}

class _QuizScreenState extends State<QuizScreen> {
  int index = 0;
  int score = 0;
  int? picked;

  void _pick(int i) {
    if (picked != null) return;
    setState(() {
      picked = i;
      if (i == quizQuestions[index].correct) score++;
    });
  }

  void _next() => setState(() {
        index++;
        picked = null;
      });

  @override
  Widget build(BuildContext context) {
    final done = index >= quizQuestions.length;
    return Scaffold(
      appBar: AppBar(title: const Text("O'zingizni sinang")),
      body: done ? _result() : _question(quizQuestions[index]),
    );
  }

  Widget _question(QuizQuestion q) {
    final answered = picked != null;
    final right = picked == q.correct;
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
      children: [
        LinearProgressIndicator(value: (index + (answered ? 1 : 0)) / quizQuestions.length, color: RColors.accent),
        const SizedBox(height: 10),
        Text('Savol ${index + 1} / ${quizQuestions.length}', style: Theme.of(context).textTheme.bodySmall),
        const SizedBox(height: 10),
        Card(child: Padding(padding: const EdgeInsets.all(16), child: Text(q.situation, style: const TextStyle(fontSize: 16, height: 1.4)))),
        const SizedBox(height: 6),
        Text('Nima qilasiz?', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        for (var i = 0; i < q.options.length; i++)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Card(
              color: !answered
                  ? null
                  : i == q.correct
                      ? RColors.of(Severity.ok).withValues(alpha: 0.18)
                      : (i == picked ? RColors.of(Severity.critical).withValues(alpha: 0.18) : null),
              child: ListTile(
                onTap: () => _pick(i),
                leading: Icon(
                  !answered ? Icons.radio_button_unchecked_rounded : (i == q.correct ? Icons.check_circle_rounded : (i == picked ? Icons.cancel_rounded : Icons.radio_button_unchecked_rounded)),
                  color: !answered ? RColors.textDim : (i == q.correct ? RColors.of(Severity.ok) : (i == picked ? RColors.of(Severity.critical) : RColors.textDim)),
                ),
                title: Text(q.options[i]),
              ),
            ),
          ),
        if (answered) ...[
          const SizedBox(height: 6),
          Text(right ? "To'g'ri!" : "Noto'g'ri", style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: RColors.of(right ? Severity.ok : Severity.critical))),
          const SizedBox(height: 6),
          Text(q.why, style: const TextStyle(height: 1.4)),
          const SizedBox(height: 16),
          FilledButton(onPressed: _next, child: Text(index + 1 < quizQuestions.length ? 'Keyingi savol' : 'Natija')),
        ],
      ],
    );
  }

  Widget _result() {
    final total = quizQuestions.length;
    final sev = score == total ? Severity.ok : (score >= total - 2 ? Severity.medium : Severity.high);
    final msg = score == total
        ? "A'lo! Siz firibgarlarning asosiy usullarini taniysiz. Bu testni yaqinlaringizga ham ko'rsating."
        : score >= total - 2
            ? "Yaxshi, lekin bir nechta vaziyat chalg'itdi. \"Firibgarlik turlari\" bo'limini yana bir ko'zdan kechiring."
            : "Firibgarlar aynan shu vaziyatlardan foydalanadi. \"Firibgarlik turlari\" bo'limini o'qib, testni qayta ishlang.";
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const SizedBox(height: 24),
        Icon(score == total ? Icons.emoji_events_rounded : Icons.school_rounded, size: 72, color: RColors.of(sev)),
        const SizedBox(height: 12),
        Text('$score / $total', textAlign: TextAlign.center, style: TextStyle(fontSize: 40, fontWeight: FontWeight.w800, color: RColors.of(sev))),
        const SizedBox(height: 12),
        Text(msg, textAlign: TextAlign.center, style: const TextStyle(height: 1.4)),
        const SizedBox(height: 24),
        FilledButton.icon(
          onPressed: () => setState(() {
            index = 0;
            score = 0;
            picked = null;
          }),
          icon: const Icon(Icons.replay_rounded),
          label: const Text('Qayta ishlash'),
        ),
      ],
    );
  }
}
