import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../core/native.dart';
import '../core/phone.dart';
import '../core/report_draft.dart';
import '../core/risk.dart';
import 'theme.dart';
import 'widgets.dart';

/// F3: saqlangan hisobotlar ro'yxati.
class ReportsScreen extends StatefulWidget {
  const ReportsScreen({super.key});
  @override
  State<ReportsScreen> createState() => _ReportsScreenState();
}

class _ReportsScreenState extends State<ReportsScreen> {
  List<Map<String, dynamic>>? items;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final r = await Native.listReports();
    if (mounted) setState(() => items = r);
  }

  Future<void> _open(Widget w) async {
    await Navigator.of(context).push(MaterialPageRoute(builder: (_) => w));
    _load();
  }

  @override
  Widget build(BuildContext context) {
    final list = items;
    return Scaffold(
      appBar: AppBar(title: const Text('Firibgarlik hisobotlari')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _open(ReportFormScreen(draft: ReportDraft())),
        icon: const Icon(Icons.add_rounded),
        label: const Text('Yangi hisobot'),
      ),
      body: list == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.fromLTRB(16, 4, 16, 96),
              children: [
                const _HowItWorks(),
                SectionTitle('Saqlangan hisobotlar (${list.length})'),
                if (list.isEmpty)
                  const Card(
                    child: ListTile(
                      leading: Icon(Icons.description_outlined, color: RColors.textDim),
                      title: Text("Hozircha hisobot yo'q"),
                      subtitle: Text("Xabar, havola, APK yoki qo'ng'iroq tekshiruvidan keyin \"Hisobot yaratish\" tugmasi chiqadi"),
                    ),
                  ),
                for (final r in list)
                  Card(
                    child: ListTile(
                      leading: Icon(r['ok'] == true ? Icons.verified_rounded : Icons.error_outline_rounded,
                          color: r['ok'] == true ? RColors.accent : RColors.of(Severity.critical)),
                      title: Text(r['ok'] == true
                          ? '${reportTargetTypes[r['targetType']] ?? r['targetType']}: '
                              '${r['targetType'] == 'phone' ? displayPhone(r['targetValue'] as String) : r['targetValue']}'
                          : '${r['name']} — buzilgan'),
                      subtitle: Text(r['ok'] == true
                          ? '${reportCategories[r['category']] ?? r['category']} · ${fmtDate(r['createdAt'] as int)}'
                          : '${r['error']}'),
                      trailing: const Icon(Icons.chevron_right_rounded),
                      onTap: () => _open(ReportViewScreen(name: r['name'] as String)),
                    ),
                  ),
              ],
            ),
    );
  }
}

class _HowItWorks extends StatelessWidget {
  const _HowItWorks();
  @override
  Widget build(BuildContext context) => Card(
        color: RColors.surfaceHi,
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Row(children: [
              Icon(Icons.draw_rounded, color: RColors.accent),
              SizedBox(width: 10),
              Expanded(child: Text('Imzolangan hisobot', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16))),
            ]),
            const SizedBox(height: 8),
            Text(
              "Hisobot telefoningizning o'zida yaratiladi va qurilma kaliti bilan imzolanadi — keyin uni hech kim "
              "sezdirmasdan o'zgartira olmaydi. ROSTOR-2 internetga chiqmaydi va hisobotni hech qayerga yubormaydi: "
              "uni 102 (IIV) ga yoki bankingizga \"Yuborish\" tugmasi orqali o'zingiz jo'natasiz.",
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ]),
        ),
      );
}

String fmtDate(int secs) {
  final d = DateTime.fromMillisecondsSinceEpoch(secs * 1000);
  String two(int x) => x.toString().padLeft(2, '0');
  return '${two(d.day)}.${two(d.month)}.${d.year} ${two(d.hour)}:${two(d.minute)}';
}

/// Hisobot formasi. Maydonlar tekshiruv natijasidan oldindan to'ldirilishi mumkin.
class ReportFormScreen extends StatefulWidget {
  const ReportFormScreen({super.key, required this.draft});
  final ReportDraft draft;
  @override
  State<ReportFormScreen> createState() => _ReportFormScreenState();
}

class _ReportFormScreenState extends State<ReportFormScreen> {
  late final ReportDraft d = widget.draft;
  late final target = TextEditingController(text: d.targetValue);
  late final org = TextEditingController(text: d.claimedOrg);
  final amount = TextEditingController();
  final desc = TextEditingController();
  final extra = TextEditingController();
  final contact = TextEditingController();
  DateTime? incident;
  String? error;
  bool busy = false;

  static const _hints = {
    'phone': '+998 90 123 45 67',
    'link': 'click-bonus.top yoki to\'liq havola',
    'apk': '64 belgili SHA-256 iz',
    'card': '8600 1234 5678 9012',
    'telegram': '@nom',
    'other': 'Qisqacha',
  };

  @override
  void dispose() {
    for (final c in [target, org, amount, desc, extra, contact]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _pickIncident() async {
    final now = DateTime.now();
    final day = await showDatePicker(
      context: context,
      initialDate: incident ?? now,
      firstDate: now.subtract(const Duration(days: 365 * 3)),
      lastDate: now,
    );
    if (day == null || !mounted) return;
    final t = await showTimePicker(context: context, initialTime: TimeOfDay.fromDateTime(incident ?? now));
    setState(() => incident = DateTime(day.year, day.month, day.day, t?.hour ?? 0, t?.minute ?? 0));
  }

  Future<void> _create() async {
    FocusScope.of(context).unfocus();
    if (d.category == null) {
      setState(() => error = 'Firibgarlik turini tanlang');
      return;
    }
    setState(() {
      busy = true;
      error = null;
    });
    final evidence = [
      for (final e in d.evidence)
        if (e.include) {'kind': e.kind, 'value': e.value},
      if (extra.text.trim().isNotEmpty) {'kind': 'note', 'value': extra.text.trim()},
    ];
    final r = await Native.createReport({
      'category': d.category,
      'targetType': d.targetType,
      'targetValue': target.text,
      'claimedOrg': org.text,
      'incidentAt': incident == null ? null : incident!.millisecondsSinceEpoch ~/ 1000,
      'amountUzs': int.tryParse(amount.text.replaceAll(RegExp(r'[^0-9]'), '')),
      'description': desc.text,
      'evidence': evidence,
      'findings': d.findings,
      'reporterContact': contact.text,
    });
    if (!mounted) return;
    if (r['error'] != null) {
      setState(() {
        busy = false;
        error = r['error'] as String;
      });
      return;
    }
    Navigator.of(context).pushReplacement(MaterialPageRoute(builder: (_) => ReportViewScreen(name: r['name'] as String, justCreated: true)));
  }

  @override
  Widget build(BuildContext context) {
    final small = Theme.of(context).textTheme.bodySmall;
    return Scaffold(
      appBar: AppBar(title: const Text('Yangi hisobot')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
        children: [
          DropdownButtonFormField<String>(
            value: d.category,
            isExpanded: true,
            decoration: const InputDecoration(labelText: 'Firibgarlik turi'),
            items: [for (final e in reportCategories.entries) DropdownMenuItem(value: e.key, child: Text(e.value))],
            onChanged: (v) => setState(() => d.category = v),
          ),
          const SectionTitle('Firibgar'),
          DropdownButtonFormField<String>(
            value: d.targetType,
            isExpanded: true,
            decoration: const InputDecoration(labelText: "Nima ma'lum"),
            items: [for (final e in reportTargetTypes.entries) DropdownMenuItem(value: e.key, child: Text(e.value))],
            onChanged: (v) => setState(() => d.targetType = v ?? 'phone'),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: target,
            keyboardType: d.targetType == 'phone' || d.targetType == 'card' ? TextInputType.phone : TextInputType.text,
            decoration: InputDecoration(labelText: reportTargetTypes[d.targetType], hintText: _hints[d.targetType]),
          ),
          if (d.targetType == 'card')
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Text("Faqat firibgar pul so'ragan karta. O'z kartangiz raqamini, muddatini yoki CVV ni yozmang.",
                  style: TextStyle(color: RColors.of(Severity.medium), fontSize: 12)),
            ),
          const SizedBox(height: 10),
          TextField(controller: org, decoration: const InputDecoration(labelText: "O'zini kim deb tanishtirdi (ixtiyoriy)", hintText: 'Masalan: Uzcard, IIV, OLX xaridori')),
          const SectionTitle('Voqea'),
          OutlinedButton.icon(
            onPressed: _pickIncident,
            icon: const Icon(Icons.event_rounded),
            label: Text(incident == null ? 'Voqea vaqtini tanlash (ixtiyoriy)' : 'Voqea vaqti: ${fmtDate(incident!.millisecondsSinceEpoch ~/ 1000)}'),
          ),
          const SizedBox(height: 10),
          TextField(controller: amount, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: "Yo'qotilgan summa, so'm (ixtiyoriy)")),
          const SizedBox(height: 10),
          TextField(controller: desc, minLines: 3, maxLines: 8, decoration: const InputDecoration(labelText: 'Nima bo\'ldi?', hintText: "Qachon, kim, nima so'radi, nima qildingiz")),
          const SectionTitle('Dalillar'),
          for (final e in d.evidence)
            Card(
              child: CheckboxListTile(
                value: e.include,
                onChanged: (v) => setState(() => e.include = v ?? false),
                title: Text(_evidenceLabel(e.kind)),
                subtitle: Text(e.value, maxLines: 4, overflow: TextOverflow.ellipsis),
              ),
            ),
          TextField(controller: extra, minLines: 1, maxLines: 5, decoration: const InputDecoration(labelText: "Qo'shimcha dalil (ixtiyoriy)", hintText: 'Masalan: SMS matni, karta raqami, havola')),
          const SectionTitle('Murojaatchi'),
          TextField(controller: contact, decoration: const InputDecoration(labelText: 'Ismingiz va telefoningiz (ixtiyoriy)')),
          const SizedBox(height: 6),
          Text("Militsiya yoki bank siz bilan bog'lanishi uchun. Yozmasangiz, hisobot anonim qoladi.", style: small),
          const SizedBox(height: 16),
          Card(
            color: RColors.of(Severity.medium).withValues(alpha: 0.12),
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Text(
                "Hisobotga o'z kartangizning muddati, CVV, PIN yoki SMS kodlarni yozmang. Ular hech qachon kerak emas.",
                style: TextStyle(color: RColors.of(Severity.medium), fontSize: 13),
              ),
            ),
          ),
          if (error != null) Padding(padding: const EdgeInsets.only(top: 12), child: Text(error!, style: TextStyle(color: RColors.of(Severity.critical)))),
          const SizedBox(height: 14),
          FilledButton.icon(
            onPressed: busy ? null : _create,
            icon: busy ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.draw_rounded),
            label: const Text('Hisobotni yaratish va imzolash'),
          ),
        ],
      ),
    );
  }
}

String _evidenceLabel(String kind) => switch (kind) {
      'sms_text' => 'Xabar matni',
      'url' => 'Havola',
      'call' => "Qo'ng'iroq",
      'apk' => 'APK fayl',
      _ => 'Izoh',
    };

/// Tayyor hisobot: o'qish uchun matn, imzo holati va yuborish.
class ReportViewScreen extends StatefulWidget {
  const ReportViewScreen({super.key, required this.name, this.justCreated = false});
  final String name;
  final bool justCreated;
  @override
  State<ReportViewScreen> createState() => _ReportViewScreenState();
}

class _ReportViewScreenState extends State<ReportViewScreen> {
  Map<String, dynamic>? r;

  @override
  void initState() {
    super.initState();
    Native.readReport(widget.name).then((v) {
      if (mounted) setState(() => r = v);
    });
  }

  Future<void> _delete() async {
    final yes = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text("Hisobotni o'chirish?"),
        content: const Text("Fayl telefondan o'chiriladi. Allaqachon yuborilgan nusxalarga ta'sir qilmaydi."),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Bekor qilish')),
          TextButton(onPressed: () => Navigator.pop(c, true), child: const Text("O'chirish")),
        ],
      ),
    );
    if (yes == true) {
      await Native.deleteReport(widget.name);
      if (mounted) Navigator.of(context).pop();
    }
  }

  @override
  Widget build(BuildContext context) {
    final v = r;
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.name),
        actions: [IconButton(tooltip: "O'chirish", onPressed: _delete, icon: const Icon(Icons.delete_outline_rounded))],
      ),
      body: v == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
              children: [
                VerdictBanner(
                  severity: v['ok'] == true ? Severity.ok : Severity.critical,
                  title: v['ok'] == true ? (widget.justCreated ? 'Hisobot tayyor va imzolangan' : 'Imzo haqiqiy') : 'Hisobot buzilgan',
                  subtitle: v['ok'] == true
                      ? "Endi uni o'zingiz yuboring: \"Yuborish\" tugmasi Telegram, pochta yoki boshqa ilovani ochadi. Matn va imzolangan .json fayl birga ketadi."
                      : 'Fayl imzosi mos kelmadi: ${v['error']}',
                ),
                if (v['ok'] == true) ...[
                  const SizedBox(height: 12),
                  FilledButton.icon(
                    onPressed: () => Native.shareReport(widget.name),
                    icon: const Icon(Icons.send_rounded),
                    label: const Text('Yuborish'),
                  ),
                  const SizedBox(height: 8),
                  OutlinedButton.icon(
                    onPressed: () {
                      Clipboard.setData(ClipboardData(text: v['readable'] as String));
                      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Matn nusxalandi')));
                    },
                    icon: const Icon(Icons.copy_rounded),
                    label: const Text('Matnni nusxalash'),
                  ),
                  const SectionTitle('Qayerga yuborish'),
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(14),
                      child: Text(
                        "• 102 — Ichki ishlar vazirligi: firibgarlik yoki tovlamachilik bo'lsa.\n"
                        "• Bankingiz — pul o'tkazilgan bo'lsa, darhol kartaning orqasidagi raqamga qo'ng'iroq qiling va "
                        "hisobotni bank so'ragan kanal orqali yuboring.\n"
                        "• Telegram akkaunti egallangan bo'lsa — yaqinlaringizni ham ogohlantiring.",
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ),
                  ),
                  const SectionTitle('Hisobot matni'),
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(14),
                      child: SelectableText(v['readable'] as String, style: const TextStyle(fontSize: 13, height: 1.4)),
                    ),
                  ),
                ],
              ],
            ),
    );
  }
}
