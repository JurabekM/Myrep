import 'package:flutter/material.dart';

import '../state/app_state.dart';
import '../theme.dart';
import 'settings_screen.dart';
import 'widgets.dart';

class ChecklistItem {
  const ChecklistItem(this.id, this.text);

  final String id;
  final String text;
}

class ChecklistGroup {
  const ChecklistGroup(this.title, this.items);

  final String title;
  final List<ChecklistItem> items;
}

/// Oila tayyorgarligi ro'yxati (JSST va qizil xoch tavsiyalari asosida). id'lar o'zgartirilmaydi —
/// bajarilganlar sozlamalarda shu id bilan saqlanadi.
const checklist = [
  ChecklistGroup('Uy zaxirasi (kamida 2 hafta)', [
    ChecklistItem('water', "Ichimlik suvi: kishi boshiga kuniga ~3 litr"),
    ChecklistItem('food', "Uzoq saqlanadigan oziq-ovqat (yorma, konserva, quruq meva)"),
    ChecklistItem('meds', "Doimiy qabul qilinadigan dorilar — kamida 1 oylik zaxira"),
    ChecklistItem('firstaid', 'Birinchi yordam qutisi, termometr, paratsetamol'),
    ChecklistItem('ors', "Og'iz orqali regidratatsiya tuzlari (ORS) — diareya va qusishda"),
    ChecklistItem('masks', 'Tibbiy niqoblar yoki FFP2 respiratorlar'),
    ChecklistItem('sanitizer', "Sovun va kamida 60% spirtli qo'l antiseptigi"),
    ChecklistItem('power', 'Powerbank, fonar, ozgina naqd pul'),
  ]),
  ChecklistGroup("Sog'liq", [
    ChecklistItem('vaccines', "Emlash kalendarini tekshiring (qizamiq, difteriya, poliomiyelit)"),
    ChecklistItem('flu_vaccine', "Mavsumiy gripp vaksinasi (ayniqsa 60+ yosh, homiladorlar, surunkali kasallar)"),
    ChecklistItem('chronic', "Surunkali kasalliklar nazorat ostida: shifokoringiz bilan reja tuzing"),
    ChecklistItem('isolation', "Uyda bemorni ajratish uchun alohida xona yoki joy rejasi"),
  ]),
  ChecklistGroup('Hujjat va aloqa', [
    ChecklistItem('records', "Emlash kartasi, allergiya va dorilar ro'yxati (qog'ozda ham)"),
    ChecklistItem('contacts', "Favqulodda kontaktlar: oila, shifokor, qo'shnilar"),
    ChecklistItem('care_plan', "Oila rejasi: kim bolalar va keksalarga qaraydi"),
    ChecklistItem('official', "Rasmiy axborot manbalarini bilib qo'ying (Sog'liqni saqlash vazirligi, JSST)"),
  ]),
  ChecklistGroup('Kundalik odatlar', [
    ChecklistItem('handwash', "Qo'lni sovun bilan kamida 20 soniya yuvish"),
    ChecklistItem('cough', "Yo'talganda og'iz-burunni tirsak bilan yopish"),
    ChecklistItem('stay_home', 'Kasal bo\'lsangiz uyda qolish'),
    ChecklistItem('ventilate', 'Xonalarni muntazam shamollatish'),
    ChecklistItem('food_safety', "Go'sht va tuxumni yaxshi pishirish, xom sutdan voz kechish"),
  ]),
];

const generalRedFlags = [
  'Nafas qisishi, ko\'krakda og\'riq yoki bosim',
  'Chalkashlik, uyg\'onishning qiyinligi, tutqanoq',
  'Bo\'yin qotishi bilan yuqori isitma yoki bosganda yo\'qolmaydigan toshma',
  'Qon ketishi (burun, milk, siydik yoki najasda)',
  'Kuchli suvsizlanish: siydik deyarli yo\'q, quruq og\'iz, holsizlik',
  "Xavfli hududdan qaytgach 3 hafta ichida isitma — safaringiz haqida ayting",
];

class PrepareScreen extends StatelessWidget {
  const PrepareScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final state = AppScope.of(context);
    final t = context.tokens;
    final done = state.settings.checklistDone.toSet();
    final total = checklist.fold<int>(0, (n, g) => n + g.items.length);
    final count = checklist.fold<int>(0, (n, g) => n + g.items.where((i) => done.contains(i.id)).length);
    return Scaffold(
      appBar: AppBar(title: const Text('Tayyorgarlik'), actions: const [SettingsButton()]),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 32),
        children: [
          InfoCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Oila tayyorgarligi: $count / $total', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: t.ink)),
                const SizedBox(height: 10),
                ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: LinearProgressIndicator(value: total == 0 ? 0 : count / total, minHeight: 10),
                ),
                const SizedBox(height: 10),
                Text(
                  "Tayyorgarlik vahima emas: epidemiya boshlansa, do'konlar va dorixonalardagi navbatlardan "
                  "qochish va yaqinlaringizni himoya qilish uchun oldindan bajariladigan oddiy qadamlar.",
                  style: TextStyle(color: t.inkMuted, height: 1.4),
                ),
              ],
            ),
          ),
          for (final g in checklist) ...[
            SectionTitle(g.title),
            InfoCard(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Column(
                children: [
                  for (final i in g.items)
                    CheckboxListTile(
                      value: done.contains(i.id),
                      onChanged: (_) => state.toggleChecklist(i.id),
                      title: Text(i.text, style: TextStyle(color: t.ink)),
                      controlAffinity: ListTileControlAffinity.leading,
                      activeColor: t.accent,
                      checkColor: t.accentInk,
                    ),
                ],
              ),
            ),
          ],
          const SectionTitle('Qachon darhol tez yordam chaqirish kerak'),
          InfoCard(borderColor: t.danger, child: BulletList(generalRedFlags, color: t.danger)),
          const MedicalDisclaimer(),
        ],
      ),
    );
  }
}
