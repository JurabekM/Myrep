import 'dart:convert';

import 'package:flutter/material.dart';

import '../core/native.dart';
import '../core/phone.dart';
import '../core/report_draft.dart';
import '../core/risk.dart';
import 'report_screen.dart';
import 'theme.dart';
import 'widgets.dart';

/// F2: Qo'ng'iroq Qalqoni. Qoidalar Kotlin'da (call/PhoneRules.kt) — qo'ng'iroq paytida ham,
/// shu ekrandagi "raqamni tekshirish" da ham aynan bir xil baholash ishlaydi.
class CallScreen extends StatefulWidget {
  const CallScreen({super.key});
  @override
  State<CallScreen> createState() => _CallScreenState();
}

Finding findingFromNative(Map<String, dynamic> m) => Finding(
      code: m['code'] as String,
      severity: Severity.values.byName(m['severity'] as String),
      title: m['title'] as String,
      explain: m['explain'] as String,
      evidence: m['evidence'] as String?,
    );

class _CallScreenState extends State<CallScreen> with WidgetsBindingObserver {
  Map<String, dynamic>? status;
  final settings = <String, bool>{};
  List<String> blocklist = [];
  List<Map<String, dynamic>> history = [];
  final ctrl = TextEditingController();
  Map<String, dynamic>? checked;
  String? checkError;

  static const _defaults = {'call_block': true, 'call_silence_intl': false, 'call_notify_official': true};

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    Native.callsChanged.addListener(_load);
    _load();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    Native.callsChanged.removeListener(_load);
    ctrl.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState s) {
    // Foydalanuvchi sozlamalardan qaytganda yoki qo'ng'iroqdan keyin holat va tarix yangilanadi.
    if (s == AppLifecycleState.resumed) _load();
  }

  Future<void> _load() async {
    final st = await Native.callStatus();
    for (final k in _defaults.keys) {
      final v = await Native.kvGet(k);
      settings[k] = v == null ? _defaults[k]! : v == '1';
    }
    final b = await Native.kvGet('call_blocklist');
    final h = await Native.kvGet('call_history');
    if (!mounted) return;
    setState(() {
      status = st;
      blocklist = b == null ? [] : (jsonDecode(b) as List).cast<String>();
      history = h == null ? [] : [for (final e in jsonDecode(h) as List) Map<String, dynamic>.from(e as Map)];
    });
  }

  Future<void> _enable() async {
    final st = await Native.requestCallRole();
    var s2 = st;
    if (st['roleHeld'] == true && st['notifications'] != true) s2 = await Native.requestNotifications();
    if (mounted) setState(() => status = s2);
  }

  Future<void> _notifications() async {
    final st = await Native.requestNotifications();
    if (st['notifications'] != true && st['notificationsAskable'] != true) await Native.open('openNotificationSettings');
    if (mounted) setState(() => status = st);
  }

  Future<void> _setFlag(String key, bool v) async {
    setState(() => settings[key] = v);
    await Native.kvSet(key, v ? '1' : '0');
  }

  Future<void> _saveBlocklist() => Native.kvSet('call_blocklist', jsonEncode(blocklist));

  Future<void> _check() async {
    final t = ctrl.text.trim();
    if (t.isEmpty) return;
    FocusScope.of(context).unfocus();
    final r = await Native.checkPhone(t);
    setState(() {
      checkError = r['error'] as String?;
      checked = checkError == null ? r : null;
    });
  }

  Future<void> _block(String n, bool add) async {
    setState(() {
      blocklist.remove(n);
      if (add) blocklist.add(n);
    });
    await _saveBlocklist();
    if (checked != null) await _check();
  }

  @override
  Widget build(BuildContext context) {
    final st = status;
    return Scaffold(
      appBar: AppBar(title: const Text("Qo'ng'iroq Qalqoni")),
      body: st == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
              children: [
                _statusBanner(st),
                const SizedBox(height: 12),
                if (st['supported'] == true) _setupCard(st),
                const SectionTitle('Raqamni tekshirish'),
                _checkCard(),
                if (st['supported'] == true) ...[
                  const SectionTitle('Sozlamalar'),
                  _settingsCard(),
                ],
                SectionTitle('Bloklangan raqamlar (${blocklist.length})'),
                _blocklistCard(),
                SectionTitle('Tarix (${history.length})'),
                _historyCard(),
                const SizedBox(height: 12),
                Text(
                  "Telegram, WhatsApp va boshqa messenjer qo'ng'iroqlari telefon tarmog'idan o'tmaydi — ularni Android "
                  "tekshirishga bermaydi. Messenjerda o'zini bank yoki IIV xodimi deb tanishtirgan odam — firibgar.",
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
    );
  }

  Widget _statusBanner(Map<String, dynamic> st) {
    if (st['supported'] != true) {
      return const VerdictBanner(
        severity: Severity.info,
        title: "Bu telefonda ishlamaydi",
        subtitle: "Qo'ng'iroqlarni tekshirish Android 10 va undan yangi versiyada ishlaydi. Raqamni qo'lda tekshirish mumkin.",
      );
    }
    final on = st['roleHeld'] == true;
    final notif = st['notifications'] == true;
    return VerdictBanner(
      severity: on ? (notif ? Severity.ok : Severity.medium) : Severity.medium,
      title: on ? (notif ? 'Qalqon yoqilgan' : "Qalqon yoqilgan, ogohlantirish o'chiq") : "Qalqon o'chiq",
      subtitle: on
          ? (notif
              ? "Har kiruvchi qo'ng'iroq telefonning o'zida, internetsiz tekshiriladi. Raqamlar hech qayerga yuborilmaydi."
              : "Firibgar raqamlar bloklanadi, lekin ogohlantirish chiqmaydi. Bildirishnomaga ruxsat bering.")
          : "Yoqilsa, ROSTOR-2 kiruvchi qo'ng'iroqni bazadagi rasmiy va firibgar raqamlar bilan solishtiradi.",
    );
  }

  Widget _setupCard(Map<String, dynamic> st) {
    final on = st['roleHeld'] == true;
    final notif = st['notifications'] == true;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          if (!on) ...[
            Text(
              "Android \"Qo'ng'iroqlarni aniqlash va spamdan himoya\" ilovasini so'raydi. ROSTOR-2 kontaktlar, "
              "qo'ng'iroqlar jurnali va suhbat ovoziga kirmaydi — faqat kiruvchi raqamni ko'radi.",
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 10),
            FilledButton.icon(onPressed: _enable, icon: const Icon(Icons.shield_rounded), label: const Text('Qalqonni yoqish')),
          ],
          if (on && !notif)
            FilledButton.icon(
              onPressed: _notifications,
              icon: const Icon(Icons.notifications_active_rounded),
              label: const Text('Ogohlantirishga ruxsat berish'),
            ),
          if (on && notif)
            OutlinedButton.icon(
              onPressed: () async {
                final ok = await Native.testCallNotification();
                if (!mounted) return;
                ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                  content: Text(ok ? "Sinov ogohlantirishi yuborildi — bildirishnomalar panelini oching" : "Bildirishnomalar o'chiq"),
                ));
              },
              icon: const Icon(Icons.notifications_rounded),
              label: const Text('Sinov ogohlantirishi'),
            ),
        ]),
      ),
    );
  }

  Widget _checkCard() {
    final c = checked;
    final findings = c == null ? const <Finding>[] : [for (final f in c['findings'] as List) findingFromNative(Map<String, dynamic>.from(f as Map))];
    final n = c?['normalized'] as String?;
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Card(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(children: [
            Expanded(
              child: TextField(
                controller: ctrl,
                keyboardType: TextInputType.phone,
                decoration: const InputDecoration(hintText: '+998 90 123 45 67', border: InputBorder.none),
                onSubmitted: (_) => _check(),
              ),
            ),
            FilledButton(onPressed: _check, child: const Text('Tekshirish')),
          ]),
        ),
      ),
      if (checkError != null)
        Padding(padding: const EdgeInsets.all(8), child: Text(checkError!, style: TextStyle(color: RColors.of(Severity.high)))),
      if (c != null) ...[
        const SizedBox(height: 8),
        Text(c['display'] as String, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800, letterSpacing: 0.5)),
        const SizedBox(height: 6),
        for (final f in sortFindings(findings)) FindingCard(f),
        if (n != null)
          Align(
            alignment: Alignment.centerLeft,
            child: TextButton.icon(
              onPressed: () => _block(n, !blocklist.contains(n)),
              icon: Icon(blocklist.contains(n) ? Icons.lock_open_rounded : Icons.block_rounded),
              label: Text(blocklist.contains(n) ? 'Blokdan chiqarish' : 'Bu raqamni bloklash'),
            ),
          ),
      ],
    ]);
  }

  Widget _settingsCard() => Card(
        child: Column(children: [
          SwitchListTile(
            value: settings['call_block'] ?? true,
            onChanged: (v) => _setFlag('call_block', v),
            title: const Text('Firibgar va bloklangan raqamlarni rad etish'),
            subtitle: const Text("Bazadagi firibgar raqamlar va siz bloklagan raqamlar qo'ng'irog'i avtomatik tugatiladi"),
          ),
          SwitchListTile(
            value: settings['call_silence_intl'] ?? false,
            onChanged: (v) => _setFlag('call_silence_intl', v),
            title: const Text('Xorijiy raqamlarni ovozsiz qilish'),
            subtitle: const Text("Qo'ng'iroq keladi, lekin jiringlamaydi. Chet eldagi qarindoshlaringiz bo'lsa, o'chiq qoldiring"),
          ),
          SwitchListTile(
            value: settings['call_notify_official'] ?? true,
            onChanged: (v) => _setFlag('call_notify_official', v),
            title: const Text("Rasmiy raqam qo'ng'iroq qilganda eslatish"),
            subtitle: const Text("Bank yoki idora raqami ko'rinsa ham, kod va karta ma'lumotini so'ramasligini eslatadi"),
          ),
        ]),
      );

  Widget _blocklistCard() => Card(
        child: blocklist.isEmpty
            ? const ListTile(
                leading: Icon(Icons.block_rounded, color: RColors.textDim),
                title: Text("Hozircha bo'sh"),
                subtitle: Text("Raqamni yuqorida tekshirib, \"Bu raqamni bloklash\" ni bosing"),
              )
            : Column(children: [
                for (final n in blocklist)
                  ListTile(
                    leading: Icon(Icons.block_rounded, color: RColors.of(Severity.high)),
                    title: Text(displayPhone(n), style: const TextStyle(fontWeight: FontWeight.w600)),
                    trailing: IconButton(
                      tooltip: 'Blokdan chiqarish',
                      icon: const Icon(Icons.close_rounded),
                      onPressed: () => _block(n, false),
                    ),
                  ),
              ]),
      );

  Widget _historyCard() => Card(
        child: history.isEmpty
            ? const ListTile(
                leading: Icon(Icons.history_rounded, color: RColors.textDim),
                title: Text("Belgilangan qo'ng'iroqlar yo'q"),
                subtitle: Text("Oddiy noma'lum raqamlar tarixga yozilmaydi — faqat rasmiy, xorijiy, yashirin va firibgar raqamlar"),
              )
            : Column(children: [
                for (final e in history)
                  ListTile(
                    leading: Icon(RColors.icon(Severity.values.byName(e['severity'] as String)),
                        color: RColors.of(Severity.values.byName(e['severity'] as String))),
                    title: Text(e['display'] as String, style: const TextStyle(fontWeight: FontWeight.w600)),
                    subtitle: Text('${e['title']} · ${_time(e['t'] as int)}'),
                    trailing: e['blocked'] == true
                        ? Text('Rad etildi', style: TextStyle(color: RColors.of(Severity.high), fontWeight: FontWeight.w700))
                        : (e['silenced'] == true ? const Text('Ovozsiz', style: TextStyle(color: RColors.textDim)) : null),
                    // Rasmiy raqam bo'lmagan qo'ng'iroq haqida hisobot (F3).
                    onTap: e['number'] == null || e['code'] == 'call.official'
                        ? null
                        : () => Navigator.of(context).push(MaterialPageRoute(
                            builder: (_) => ReportFormScreen(draft: draftFromCall(e, _time(e['t'] as int))))),
                  ),
                TextButton(
                  onPressed: () async {
                    await Native.kvSet('call_history', '[]');
                    setState(() => history = []);
                  },
                  child: const Text('Tarixni tozalash'),
                ),
              ]),
      );

  String _time(int ms) {
    final d = DateTime.fromMillisecondsSinceEpoch(ms);
    String two(int x) => x.toString().padLeft(2, '0');
    return '${two(d.day)}.${two(d.month)}.${d.year} ${two(d.hour)}:${two(d.minute)}';
  }
}
