import 'dart:typed_data';

import 'package:flutter/material.dart';

import '../core/app_state.dart';
import '../core/native.dart';
import '../core/report_draft.dart';
import '../core/risk.dart';
import '../engine/apk_rules.dart';
import 'report_screen.dart';
import 'theme.dart';
import 'widgets.dart';

/// APK Qalqon ekrani. `uri` berilsa (Telegram'dan "ROSTOR-2 bilan ochish") darhol tahlil
/// qiladi, aks holda fayl tanlash oynasini ochadi.
class ApkScreen extends StatefulWidget {
  const ApkScreen({super.key, this.uri});
  final String? uri;
  @override
  State<ApkScreen> createState() => _ApkScreenState();
}

class _ApkScreenState extends State<ApkScreen> {
  ApkReport? report;
  bool busy = false;
  String? error;

  @override
  void initState() {
    super.initState();
    if (widget.uri != null) _run(() => Native.inspectUri(widget.uri!));
  }

  Future<void> _run(Future<Map<String, dynamic>?> Function() get) async {
    setState(() { busy = true; error = null; });
    try {
      final facts = await get();
      if (!mounted) return;
      setState(() => report = facts == null ? report : evaluateApk(facts, AppState.instance.db));
    } catch (e) {
      if (mounted) setState(() => error = '$e');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('APK Qalqon')),
      body: busy
          ? const Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
              CircularProgressIndicator(color: RColors.accent),
              SizedBox(height: 16),
              Text("Imzo va ruxsatlar tekshirilmoqda…"),
            ]))
          : ListView(
              padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
              children: [
                if (report == null) ..._intro() else ..._result(report!),
                if (error != null) Padding(padding: const EdgeInsets.only(top: 12), child: Text(error!, style: TextStyle(color: RColors.of(Severity.critical)))),
                const SizedBox(height: 16),
                FilledButton.icon(
                  onPressed: () => _run(Native.pickApk),
                  icon: const Icon(Icons.folder_open_rounded),
                  label: Text(report == null ? 'APK faylni tanlash' : 'Boshqa faylni tekshirish'),
                ),
              ],
            ),
    );
  }

  List<Widget> _intro() => [
        const SizedBox(height: 8),
        const Icon(Icons.android_rounded, size: 72, color: RColors.accent),
        const SizedBox(height: 12),
        const Text("Ilova faylini o'rnatishdan oldin tekshiring",
            textAlign: TextAlign.center, style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
        const SizedBox(height: 12),
        const Card(child: Padding(
          padding: EdgeInsets.all(16),
          child: Text(
            "Eng qulay yo'l: Telegram'da .apk faylni bosganda \"ROSTOR-2 bilan ochish\"ni tanlang. "
            "ROSTOR-2 faylni o'rnatmaydi — faqat imzosi, ruxsatlari va telefoningizdagi rasmiy ilovalar bilan "
            "solishtiradi. Hammasi telefonning o'zida, internetsiz bajariladi.",
          ),
        )),
      ];

  List<Widget> _result(ApkReport r) {
    final f = r.facts;
    final sev = r.severity;
    final sub = switch (sev) {
      Severity.critical || Severity.high =>
        "O'rnatmang va faylni o'chiring. Uni tanishingiz yuborgan bo'lsa, uning akkaunti buzilgan bo'lishi mumkin — ogohlantiring.",
      Severity.medium => "Shubhali belgilar bor. Ilovani Google Play'dan topib o'rnatish xavfsizroq.",
      Severity.ok => "Imzo rasmiy yoki telefoningizdagi ilova bilan bir xil.",
      _ => "Jiddiy belgi topilmadi, lekin bu kafolat emas. Imkon bo'lsa Google Play'dan o'rnating.",
    };
    final signers = (f['signers'] as List? ?? const []).cast<Map<String, dynamic>>();
    final perms = (f['permissions'] as List? ?? const []).cast<String>();
    return [
      Row(children: [
        AppIcon(bytes: f['icon'] is Uint8List ? f['icon'] as Uint8List : null, size: 52),
        const SizedBox(width: 14),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(r.label ?? (f['fileName'] as String? ?? 'Noma\'lum fayl'), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
          if (r.packageName != null) Text(r.packageName!, style: Theme.of(context).textTheme.bodySmall),
        ])),
      ]),
      const SizedBox(height: 14),
      VerdictBanner(severity: sev, title: verdictTitle(sev), subtitle: sub),
      const SectionTitle('Topilmalar'),
      for (final x in r.findings) Padding(padding: const EdgeInsets.only(bottom: 8), child: FindingCard(x)),
      if (sev >= Severity.high && f['fileSha256'] != null)
        OutlinedButton.icon(
          onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ReportFormScreen(draft: draftFromApk(r)))),
          icon: const Icon(Icons.description_rounded),
          label: const Text('Firibgarlik haqida hisobot yaratish'),
        ),
      if (f['ok'] == true) ...[
        const SectionTitle('Texnik ma\'lumot'),
        Card(child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            if (f['fileName'] != null) KV('Fayl', f['fileName'] as String),
            if (f['fileSize'] is int && (f['fileSize'] as int) > 0) KV('Hajmi', _size(f['fileSize'] as int)),
            if (f['versionName'] != null) KV('Versiya', '${f['versionName']} (${f['versionCode']})'),
            if (f['targetSdk'] != null) KV('targetSdk', '${f['targetSdk']}'),
            KV('Imzo sxemasi', ((f['sigSchemes'] as List?) ?? const []).join(', ').ifEmpty('—')),
            KV('Ruxsatlar', '${perms.length} ta'),
            if (f['fileSha256'] != null) KV('Fayl SHA-256', f['fileSha256'] as String, mono: true),
            for (final s in signers) ...[
              const SizedBox(height: 8),
              Text('Imzolovchi sertifikat (SHA-256)', style: Theme.of(context).textTheme.bodySmall),
              const SizedBox(height: 6),
              Fingerprint(s['sha256'] as String),
              const SizedBox(height: 4),
              Text(s['subject'] as String? ?? '', style: Theme.of(context).textTheme.bodySmall),
            ],
          ]),
        )),
        if (perms.isNotEmpty) ...[
          const SectionTitle("So'ralgan ruxsatlar"),
          Card(child: Padding(
            padding: const EdgeInsets.all(14),
            child: SelectableText(perms.map((p) => p.replaceFirst('android.permission.', '')).join('\n'),
                style: const TextStyle(fontFamily: 'monospace', fontSize: 12, color: RColors.textDim)),
          )),
        ],
      ],
    ];
  }
}

String _size(int bytes) =>
    bytes >= 1048576 ? '${(bytes / 1048576).toStringAsFixed(1)} MB' : '${(bytes / 1024).toStringAsFixed(1)} KB';

extension on String {
  String ifEmpty(String other) => isEmpty ? other : this;
}
