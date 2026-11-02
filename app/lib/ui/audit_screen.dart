import 'package:flutter/material.dart';

import '../core/app_state.dart';
import '../core/native.dart';
import '../core/risk.dart';
import '../engine/audit_rules.dart';
import 'theme.dart';
import 'widgets.dart';

class AuditScreen extends StatefulWidget {
  const AuditScreen({super.key});
  @override
  State<AuditScreen> createState() => _AuditScreenState();
}

class _AuditScreenState extends State<AuditScreen> {
  final state = AppState.instance;
  DeviceAudit? audit;
  String? error;
  bool showAll = false;

  @override
  void initState() {
    super.initState();
    _run();
  }

  Future<void> _run() async {
    setState(() { audit = null; error = null; });
    try {
      final a = await state.runAudit();
      if (mounted) setState(() => audit = a);
    } catch (e) {
      if (mounted) setState(() => error = '$e');
    }
  }

  /// Foydalanuvchi "ishonaman" degan ilova ro'yxatda xavf darajasini ko'rsatmaydi (Q2).
  Severity _shown(AppAudit a) => state.trustedApps.contains(a.packageName) ? Severity.info : a.severity;

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: state,
      builder: (context, _) {
        final a = audit;
        return Scaffold(
          appBar: AppBar(
            title: const Text('Qurilma auditi'),
            actions: [if (a != null) IconButton(tooltip: 'Qayta tekshirish', onPressed: _run, icon: const Icon(Icons.refresh_rounded))],
          ),
          body: error != null
              ? Center(child: Padding(padding: const EdgeInsets.all(24), child: Text(error!)))
              : a == null
                  ? const Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
                      CircularProgressIndicator(color: RColors.accent),
                      SizedBox(height: 16),
                      Text("Ilovalar va sozlamalar tekshirilmoqda…"),
                    ]))
                  : _body(a),
        );
      },
    );
  }

  Widget _body(DeviceAudit a) {
    final flagged = a.apps.where((x) => _shown(x) >= Severity.medium).toList()
      ..sort((x, y) => _shown(y).index.compareTo(_shown(x).index));
    final rest = a.apps.where((x) => _shown(x) < Severity.medium).toList()
      ..sort((x, y) => x.label.toLowerCase().compareTo(y.label.toLowerCase()));
    final worst = worstOf([...a.deviceFindings, for (final x in flagged) Finding(code: '', severity: _shown(x), title: '', explain: '')]);
    final sub = switch (worst) {
      Severity.critical || Severity.high => "Quyidagi ilovalarni darhol ko'rib chiqing. Har birida nima qilish kerakligi yozilgan.",
      Severity.medium => "Bir nechta narsa e'tibor talab qiladi.",
      _ => "Kuchli ruxsatga ega shubhali ilova topilmadi.",
    };
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
      children: [
        VerdictBanner(severity: worst, title: verdictTitle(worst), subtitle: sub),
        const SizedBox(height: 6),
        Text("${a.apps.length} ta ilova tekshirildi · ${_time(a.scannedAt)}", style: Theme.of(context).textTheme.bodySmall),
        if (a.deviceFindings.isNotEmpty) ...[
          const SectionTitle('Telefon sozlamalari'),
          for (final f in a.deviceFindings) Padding(padding: const EdgeInsets.only(bottom: 8), child: FindingCard(f)),
        ],
        if (flagged.isNotEmpty) ...[
          SectionTitle("E'tibor talab qiladi (${flagged.length})"),
          for (final x in flagged) _appTile(x),
        ],
        SectionTitle("Qolgan ilovalar (${rest.length})"),
        if (!showAll)
          OutlinedButton(onPressed: () => setState(() => showAll = true), child: Text("${rest.length} ta ilovani ko'rsatish"))
        else
          for (final x in rest) _appTile(x),
      ],
    );
  }

  Widget _appTile(AppAudit x) {
    final sev = _shown(x);
    final top = x.findings.isEmpty ? null : x.findings.first;
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Card(
        child: ListTile(
          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
          leading: AppIcon(package: x.packageName),
          title: Text(x.label, maxLines: 1, overflow: TextOverflow.ellipsis),
          subtitle: Text(
            state.trustedApps.contains(x.packageName) ? 'Siz ishonchli deb belgilagansiz' : (top?.title ?? x.sourceName),
            maxLines: 2, overflow: TextOverflow.ellipsis, style: Theme.of(context).textTheme.bodySmall,
          ),
          trailing: sev >= Severity.medium ? SeverityChip(sev) : null,
          onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => AppDetailScreen(app: x))),
        ),
      ),
    );
  }

  String _time(DateTime t) => '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}';
}

class AppDetailScreen extends StatelessWidget {
  const AppDetailScreen({super.key, required this.app});
  final AppAudit app;

  static const _dangerous = {
    'READ_SMS', 'RECEIVE_SMS', 'SEND_SMS', 'READ_CALL_LOG', 'CALL_PHONE', 'READ_CONTACTS', 'RECORD_AUDIO',
    'CAMERA', 'ACCESS_FINE_LOCATION', 'ACCESS_BACKGROUND_LOCATION', 'READ_PHONE_STATE', 'ANSWER_PHONE_CALLS',
    'READ_MEDIA_IMAGES', 'READ_EXTERNAL_STORAGE', 'BODY_SENSORS', 'POST_NOTIFICATIONS',
  };

  @override
  Widget build(BuildContext context) {
    final state = AppState.instance;
    final f = app.facts;
    final granted = ((f['granted'] as List?) ?? const []).cast<String>()
        .map((p) => p.replaceFirst('android.permission.', ''))
        .where(_dangerous.contains).toList();
    final certs = ((f['certSha256'] as List?) ?? const []).cast<String>();
    return ListenableBuilder(
      listenable: state,
      builder: (context, _) {
        final trusted = state.trustedApps.contains(app.packageName);
        return Scaffold(
          appBar: AppBar(title: Text(app.label, overflow: TextOverflow.ellipsis)),
          body: ListView(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
            children: [
              Row(children: [
                AppIcon(package: app.packageName, size: 52),
                const SizedBox(width: 14),
                Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(app.label, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                  Text(app.packageName, style: Theme.of(context).textTheme.bodySmall),
                ])),
              ]),
              const SizedBox(height: 14),
              if (app.findings.isEmpty)
                const VerdictBanner(severity: Severity.ok, title: 'Jiddiy belgi yo\'q', subtitle: "Bu ilovada kuchli xavfli imkoniyat topilmadi.")
              else ...[
                for (final x in app.findings) Padding(padding: const EdgeInsets.only(bottom: 8), child: FindingCard(x, dimmed: trusted)),
              ],
              const SectionTitle("Ma'lumot"),
              Card(child: Padding(
                padding: const EdgeInsets.all(14),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  KV('Manba', app.sourceName),
                  if (f['versionName'] != null) KV('Versiya', '${f['versionName']}'),
                  if (f['firstInstall'] is int) KV("O'rnatilgan", _date(f['firstInstall'] as int)),
                  if (f['lastUpdate'] is int) KV('Yangilangan', _date(f['lastUpdate'] as int)),
                  KV('Ruxsatlar', granted.isEmpty ? "Xavfli ruxsat berilmagan" : granted.join(', ')),
                  if (certs.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    Text('Imzo sertifikati (SHA-256)', style: Theme.of(context).textTheme.bodySmall),
                    const SizedBox(height: 6),
                    Fingerprint(certs.first),
                  ],
                ]),
              )),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: () => Native.open('openAppDetails', app.packageName),
                icon: const Icon(Icons.settings_applications_rounded),
                label: const Text("Ilova sozlamalari (o'chirish shu yerda)"),
              ),
              if (app.findings.isNotEmpty) ...[
                const SizedBox(height: 10),
                OutlinedButton.icon(
                  onPressed: () => state.setTrusted(app.packageName, !trusted),
                  icon: Icon(trusted ? Icons.undo_rounded : Icons.thumb_up_alt_outlined),
                  label: Text(trusted ? "Ishonchli belgisini olib tashlash" : "Bu ilovani bilaman, ishonaman"),
                ),
              ],
            ],
          ),
        );
      },
    );
  }

  String _date(int ms) {
    final d = DateTime.fromMillisecondsSinceEpoch(ms);
    return '${d.day.toString().padLeft(2, '0')}.${d.month.toString().padLeft(2, '0')}.${d.year}';
  }
}
