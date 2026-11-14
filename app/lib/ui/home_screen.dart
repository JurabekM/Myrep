import 'package:flutter/material.dart';

import '../core/app_state.dart';
import '../core/risk.dart';
import 'apk_screen.dart';
import 'audit_screen.dart';
import 'call_screen.dart';
import 'check_screen.dart';
import 'learn_screen.dart';
import 'quiz_screen.dart';
import 'report_screen.dart';
import 'self_screen.dart';
import 'theme.dart';
import 'widgets.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> with WidgetsBindingObserver {
  final state = AppState.instance;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState s) {
    // Q4: fon xizmati yo'q — ilova ochilganda nima o'zgarganini so'raymiz.
    if (s == AppLifecycleState.resumed) state.refreshChanges().catchError((_) {});
  }

  void _go(Widget w) => Navigator.of(context).push(MaterialPageRoute(builder: (_) => w));

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: state,
      builder: (context, _) => Scaffold(
        appBar: AppBar(
          title: const Row(children: [
            Icon(Icons.shield_rounded, color: RColors.accent),
            SizedBox(width: 10),
            Text('ROSTOR-2'),
          ]),
          actions: [
            IconButton(
              tooltip: 'ROSTOR-2 haqiqiymi?',
              icon: const Icon(Icons.fingerprint_rounded),
              onPressed: () => _go(const SelfScreen()),
            ),
          ],
        ),
        body: ListView(
          padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
          children: [
            _statusCard(),
            if (state.changedPackages.isNotEmpty) ...[const SizedBox(height: 12), _changesCard()],
            const SectionTitle('Tekshirish'),
            _tile(Icons.android_rounded, "APK faylni tekshirish",
                "Telegram yoki brauzerdan kelgan ilova faylini o'rnatishdan oldin", () => _go(const ApkScreen())),
            const SizedBox(height: 10),
            _tile(Icons.link_rounded, "Havola yoki xabarni tekshirish",
                "SMS, Telegram xabari yoki sayt manzilini qo'yib tekshiring", () => _go(const CheckScreen())),
            const SizedBox(height: 10),
            _tile(Icons.phonelink_lock_rounded, "Qurilma auditi",
                "Qaysi ilova ekraningizni, SMS va bildirishnomalaringizni ko'ra oladi", () => _go(const AuditScreen())),
            const SectionTitle('Himoya'),
            _tile(Icons.phone_callback_rounded, "Qo'ng'iroq Qalqoni",
                "Kiruvchi qo'ng'iroq rasmiy, firibgar yoki xorijiy raqamdanmi — qo'ng'iroq paytida ogohlantiradi",
                () => _go(const CallScreen())),
            const SizedBox(height: 10),
            _tile(Icons.description_rounded, "Firibgarlik haqida hisobot",
                "Imzolangan hisobot yarating va uni 102 yoki bankka o'zingiz yuboring", () => _go(const ReportsScreen())),
            const SectionTitle("O'rganish"),
            _tile(Icons.school_rounded, "Firibgarlik turlari",
                "Eng ko'p uchraydigan 7 usul va ulardan himoyalanish", () => _go(const LearnScreen())),
            const SizedBox(height: 10),
            _tile(Icons.quiz_rounded, "O'zingizni sinang",
                "9 ta haqiqiy vaziyat: firibgarni taniy olasizmi?", () => _go(const QuizScreen())),
            const SizedBox(height: 18),
            _footer(),
          ],
        ),
      ),
    );
  }

  Widget _statusCard() {
    final audit = state.lastAudit;
    final sev = audit?.severity;
    final c = sev == null ? RColors.accent : RColors.of(sev);
    final title = audit == null
        ? 'Qurilma hali tekshirilmagan'
        : switch (sev!) {
            Severity.critical || Severity.high => 'Xavf topildi',
            Severity.medium => "E'tibor talab qiladi",
            _ => 'Jiddiy xavf topilmadi',
          };
    final sub = audit == null
        ? "Auditni bir marta ishga tushiring: kuchli ruxsatlarga ega ilovalar ko'rsatiladi."
        : '${audit.flagged.length} ta ilova va ${audit.deviceFindings.length} ta sozlama e\'tibor talab qiladi.';
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Container(
                width: 56, height: 56,
                decoration: BoxDecoration(shape: BoxShape.circle, color: c.withValues(alpha: 0.15)),
                child: Icon(sev == null ? Icons.shield_outlined : RColors.icon(sev), color: c, size: 32),
              ),
              const SizedBox(width: 14),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(title, style: TextStyle(color: c, fontSize: 18, fontWeight: FontWeight.w800)),
                const SizedBox(height: 4),
                Text(sub, style: Theme.of(context).textTheme.bodySmall),
              ])),
            ]),
            const SizedBox(height: 14),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: () => _go(const AuditScreen()),
                icon: const Icon(Icons.radar_rounded),
                label: Text(audit == null ? 'Qurilmani tekshirish' : 'Qayta tekshirish'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _changesCard() => Card(
        color: RColors.surfaceHi,
        child: ListTile(
          leading: const Icon(Icons.new_releases_rounded, color: RColors.accent),
          title: Text("Oxirgi tekshiruvdan beri ${state.changedPackages.length} ta ilova o'rnatildi yoki yangilandi"),
          subtitle: const Text("Ularni tekshirish uchun bosing"),
          onTap: () => _go(const AuditScreen()),
        ),
      );

  Widget _tile(IconData icon, String title, String sub, VoidCallback onTap) => Card(
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Row(children: [
              Container(
                width: 46, height: 46,
                decoration: BoxDecoration(color: RColors.accent.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(12)),
                child: Icon(icon, color: RColors.accent),
              ),
              const SizedBox(width: 14),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(title, style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 3),
                Text(sub, style: Theme.of(context).textTheme.bodySmall),
              ])),
              const Icon(Icons.chevron_right_rounded, color: RColors.textDim),
            ]),
          ),
        ),
      );

  Widget _footer() {
    final s = state.self;
    final noNet = s != null && s['hasInternet'] == false;
    final db = state.dbStatus;
    return InkWell(
      onTap: () => _go(const SelfScreen()),
      borderRadius: BorderRadius.circular(12),
      child: Padding(
        padding: const EdgeInsets.all(8),
        child: Wrap(
          alignment: WrapAlignment.center,
          spacing: 8,
          runSpacing: 8,
          children: [
            _pill(noNet ? Icons.wifi_off_rounded : Icons.wifi_rounded,
                s == null ? 'Tekshirilmoqda…' : (noNet ? "Internet ruxsati yo'q" : 'Internet ruxsati bor (sinov versiyasi)'),
                noNet ? RColors.of(Severity.ok) : RColors.of(Severity.medium)),
            _pill(db.ok ? Icons.verified_rounded : Icons.error_outline_rounded,
                db.ok ? 'Baza v${db.version} · imzo tekshirildi' : 'Baza: ${db.error}',
                db.ok ? RColors.of(Severity.ok) : RColors.of(Severity.critical)),
          ],
        ),
      ),
    );
  }

  Widget _pill(IconData i, String t, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20)),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(i, size: 16, color: c),
          const SizedBox(width: 6),
          Flexible(child: Text(t, style: TextStyle(color: c, fontSize: 12, fontWeight: FontWeight.w600))),
        ]),
      );
}
