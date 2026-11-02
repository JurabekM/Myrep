import 'package:flutter/material.dart';

import '../core/app_state.dart';
import '../core/native.dart';
import '../core/risk.dart';
import 'theme.dart';
import 'widgets.dart';

/// Q3: "ROSTOR-2 haqiqiymi?" — foydalanuvchi o'z nusxasini rasmiy imzo izi bilan solishtiradi.
class SelfScreen extends StatelessWidget {
  const SelfScreen({super.key});

  static const _permInfo = {
    'android.permission.QUERY_ALL_PACKAGES': "Qurilma auditi: qaysi ilovalar o'rnatilganini ko'rish uchun",
    'android.permission.POST_NOTIFICATIONS': "Qo'ng'iroq Qalqoni: shubhali qo'ng'iroq haqida ogohlantirish uchun",
  };

  @override
  Widget build(BuildContext context) {
    final state = AppState.instance;
    final s = state.self;
    final db = state.dbStatus;
    if (s == null) return Scaffold(appBar: AppBar(title: const Text('ROSTOR-2 haqiqiymi?')), body: const Center(child: CircularProgressIndicator()));
    final certs = ((s['certSha256'] as List?) ?? const []).cast<String>();
    final perms = ((s['permissions'] as List?) ?? const []).cast<String>()
        .where((p) => !p.endsWith('DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION')).toList();
    final hasNet = s['hasInternet'] == true;
    final debuggable = s['debuggable'] == true;
    final inst = Map<String, dynamic>.from((s['installer'] as Map?) ?? const {});
    final fromPlay = inst['installing'] == 'com.android.vending';
    return Scaffold(
      appBar: AppBar(title: const Text('ROSTOR-2 haqiqiymi?')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
        children: [
          VerdictBanner(
            severity: hasNet && !debuggable ? Severity.critical : (debuggable ? Severity.medium : Severity.ok),
            title: hasNet && !debuggable ? 'Diqqat: bu nusxa shubhali' : (debuggable ? 'Sinov versiyasi' : "Internetga chiqa olmaydi"),
            subtitle: hasNet && !debuggable
                ? "Rasmiy ROSTOR-2 da internet ruxsati yo'q. Bu nusxada bor — uni o'chirib, Google Play'dan o'rnating."
                : debuggable
                    ? "Bu dasturchining sinov yig'ilishi. Rasmiy relizda internet ruxsati umuman bo'lmaydi."
                    : "Ilovada INTERNET ruxsati yo'q: u hech qanday ma'lumotni telefondan tashqariga yubora olmaydi.",
          ),
          const SectionTitle('Imzo izi'),
          Text(
            "Rasmiy ROSTOR-2 har doim bitta kalit bilan imzolanadi. Quyidagi izni rasmiy sayt va reliz eslatmasidagi "
            "iz bilan solishtiring. Bitta belgi farq qilsa ham — bu soxta nusxa.",
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: 10),
          for (final c in certs) Fingerprint(c),
          if ((s['expectedCert'] as String? ?? '').isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: certs.contains(s['expectedCert'])
                  ? Text("Ichki tekshiruv: imzo reliz kaliti bilan mos.", style: TextStyle(color: RColors.of(Severity.ok), fontSize: 13))
                  // Qayta imzolangan nusxa (kod o'zgarmagan) shu yerda ushlanadi; kodni ham o'zgartirgan
                  // firibgar bu tekshiruvni o'chira oladi — shuning uchun izni tashqi manba bilan solishtirish asosiy.
                  : Text("Ichki tekshiruv: imzo reliz kalitiga MOS EMAS — bu qayta imzolangan soxta nusxa. O'chiring.",
                      style: TextStyle(color: RColors.of(Severity.critical), fontWeight: FontWeight.w700, fontSize: 13)),
            ),
          const SectionTitle("O'rnatish manbasi"),
          Card(child: ListTile(
            leading: Icon(fromPlay ? Icons.shop_rounded : Icons.file_present_rounded, color: fromPlay ? RColors.of(Severity.ok) : RColors.of(Severity.medium)),
            title: Text(fromPlay ? 'Google Play' : (inst['installing'] as String? ?? "Noma'lum (APK fayl)")),
            subtitle: Text(fromPlay ? 'Rasmiy tarqatish kanali' : "ROSTOR-2 QR kod yoki Telegram fayli orqali tarqatilmaydi"),
          )),
          const SectionTitle('Tekshiruv bazasi'),
          Card(child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              KV('Holati', db.ok ? 'Imzo tekshirildi (Ed25519 + ML-DSA-65)' : 'Xato: ${db.error}'),
              KV('Versiya', db.ok ? 'v${db.version}' : '—'),
              if (db.issuedAt > 0) KV('Chiqarilgan', _date(db.issuedAt)),
              KV('Kalit ID', (s['dbKeyId'] as String?) ?? '—', mono: true),
              KV('Tashkilotlar', '${state.db.organizations.length} ta rasmiy tashkilot'),
              const SizedBox(height: 6),
              Text("Baza faqat ilovaning yangi versiyasi bilan yangilanadi.", style: Theme.of(context).textTheme.bodySmall),
            ]),
          )),
          const SectionTitle('Ruxsatlar'),
          Card(child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              for (final p in perms)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 6),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(p.replaceFirst('android.permission.', ''), style: const TextStyle(fontFamily: 'monospace', fontSize: 13)),
                    Text(_permInfo[p] ?? (p.contains('INTERNET') ? "Faqat sinov versiyasida" : ''), style: Theme.of(context).textTheme.bodySmall),
                  ]),
                ),
              const SizedBox(height: 6),
              Text("Maxsus imkoniyatlar (Accessibility), SMS, kontaktlar va barcha fayllarga kirish ruxsati so'ralmaydi.",
                  style: Theme.of(context).textTheme.bodySmall),
            ]),
          )),
          const SectionTitle('Hisobot kaliti'),
          FutureBuilder<Map<String, dynamic>>(
            future: Native.reportIdentity(),
            builder: (context, snap) {
              final id = snap.data;
              return Card(child: Padding(
                padding: const EdgeInsets.all(14),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  if (id?['exists'] == true) ...[
                    KV('Qurilma ID', id!['deviceId'] as String, mono: true),
                    const SizedBox(height: 6),
                  ],
                  Text(
                    id?['exists'] == true
                        ? "Hisobotlaringiz shu kalit bilan imzolanadi. Kalit telefondan chiqmaydi va zaxira nusxaga tushmaydi."
                        : "Kalit birinchi hisobot yaratilganda telefonning o'zida paydo bo'ladi.",
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ]),
              ));
            },
          ),
          const SectionTitle('Ilova'),
          Card(child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(children: [
              KV('Paket', s['packageName'] as String),
              KV('Versiya', '${s['versionName']} (${s['versionCode']})'),
            ]),
          )),
        ],
      ),
    );
  }

  String _date(int secs) {
    final d = DateTime.fromMillisecondsSinceEpoch(secs * 1000);
    return '${d.day.toString().padLeft(2, '0')}.${d.month.toString().padLeft(2, '0')}.${d.year}';
  }
}
