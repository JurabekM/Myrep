import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../core/app_state.dart';
import '../core/report_draft.dart';
import '../core/risk.dart';
import '../engine/text_rules.dart';
import 'report_screen.dart';
import 'widgets.dart';

/// Havola Qalqoni + Xabar tekshiruvi: bitta maydon, matn ichidagi havolalar alohida baholanadi.
class CheckScreen extends StatefulWidget {
  const CheckScreen({super.key, this.initialText});
  final String? initialText;
  @override
  State<CheckScreen> createState() => _CheckScreenState();
}

class _CheckScreenState extends State<CheckScreen> {
  final ctrl = TextEditingController();
  TextReport? report;

  @override
  void initState() {
    super.initState();
    if (widget.initialText != null && widget.initialText!.trim().isNotEmpty) {
      ctrl.text = widget.initialText!;
      // initState ichida FocusScope.of(context) chaqirib bo'lmaydi — faqat tahlil.
      report = analyzeText(ctrl.text.trim(), AppState.instance.db);
    }
  }

  @override
  void dispose() {
    ctrl.dispose();
    super.dispose();
  }

  void _check() {
    final t = ctrl.text.trim();
    if (t.isEmpty) return;
    FocusScope.of(context).unfocus();
    setState(() => report = analyzeText(t, AppState.instance.db));
  }

  Future<void> _paste() async {
    final d = await Clipboard.getData(Clipboard.kTextPlain);
    if (d?.text != null) {
      ctrl.text = d!.text!;
      _check();
    }
  }

  @override
  Widget build(BuildContext context) {
    final r = report;
    return Scaffold(
      appBar: AppBar(title: const Text('Havola va xabar')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
        children: [
          TextField(
            controller: ctrl,
            minLines: 3,
            maxLines: 8,
            decoration: const InputDecoration(hintText: "SMS, Telegram xabari yoki sayt manzilini shu yerga qo'ying"),
          ),
          const SizedBox(height: 10),
          Row(children: [
            Expanded(child: OutlinedButton.icon(onPressed: _paste, icon: const Icon(Icons.content_paste_rounded), label: const Text("Qo'yish"))),
            const SizedBox(width: 10),
            Expanded(child: FilledButton.icon(onPressed: _check, icon: const Icon(Icons.search_rounded), label: const Text('Tekshirish'))),
          ]),
          if (r == null) ...[
            const SizedBox(height: 16),
            Text(
              "Maslahat: istalgan ilovada matnni belgilab, menyudan \"ROSTOR-2 bilan tekshirish\"ni tanlang "
              "yoki xabarni \"Ulashish\" orqali ROSTOR-2 ga yuboring.",
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ] else ...[
            const SizedBox(height: 16),
            VerdictBanner(severity: r.severity, title: verdictTitle(r.severity), subtitle: _advice(r.severity)),
            if (r.findings.isNotEmpty) ...[
              const SectionTitle('Xabar matni'),
              for (final f in r.findings) Padding(padding: const EdgeInsets.only(bottom: 8), child: FindingCard(f)),
            ],
            for (final l in r.links) ...[
              SectionTitle('Havola: ${l.host ?? l.input}'),
              for (final f in l.findings) Padding(padding: const EdgeInsets.only(bottom: 8), child: FindingCard(f)),
            ],
            if (r.severity >= Severity.medium) ...[
              const SizedBox(height: 8),
              OutlinedButton.icon(
                onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ReportFormScreen(draft: draftFromText(r)))),
                icon: const Icon(Icons.description_rounded),
                label: const Text('Firibgarlik haqida hisobot yaratish'),
              ),
            ],
          ],
        ],
      ),
    );
  }

  String _advice(Severity s) => switch (s) {
        Severity.critical => "Javob bermang, havolani ochmang, kod yoki karta ma'lumotini aytmang. Bankka kartaning orqasidagi raqam orqali o'zingiz qo'ng'iroq qiling.",
        Severity.high => "Firibgarlikning aniq belgilari bor. Hech qanday harakat qilmasdan oldin mustaqil tekshiring.",
        Severity.medium => "Shubhali belgilar bor. Ehtiyot bo'ling.",
        Severity.ok => "Rasmiy manba. Baribir SMS kod va CVV'ni hech kimga bermang.",
        _ => "Ma'lum belgi topilmadi. Bu kafolat emas: kod, CVV yoki oldindan to'lov so'ralsa — firibgarlik.",
      };
}
