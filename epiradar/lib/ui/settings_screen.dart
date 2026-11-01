import 'package:flutter/material.dart';

import '../data/models.dart';
import '../state/app_state.dart';
import '../theme.dart';
import '../util/format.dart';
import 'widgets.dart';

class SettingsButton extends StatelessWidget {
  const SettingsButton({super.key});

  @override
  Widget build(BuildContext context) => IconButton(
        tooltip: 'Sozlamalar',
        icon: const Icon(Icons.settings_outlined),
        onPressed: () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const SettingsScreen())),
      );
}

/// Mamlakat tanlash (qidiruvli). Tanlangan ISO3 yoki null qaytaradi.
Future<String?> pickCountry(BuildContext context, {String title = 'Mamlakatni tanlang', Set<String> exclude = const {}}) =>
    Navigator.of(context).push<String>(
      MaterialPageRoute(fullscreenDialog: true, builder: (_) => _CountryPicker(title: title, exclude: exclude)),
    );

class _CountryPicker extends StatefulWidget {
  const _CountryPicker({required this.title, required this.exclude});

  final String title;
  final Set<String> exclude;

  @override
  State<_CountryPicker> createState() => _CountryPickerState();
}

class _CountryPickerState extends State<_CountryPicker> {
  String query = '';

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final q = query.trim().toLowerCase();
    final all = AppScope.of(context).catalog.countries;
    final list = all
        .where((c) => !widget.exclude.contains(c.iso3))
        .where((c) => q.isEmpty || c.name.toLowerCase().contains(q) || c.nameEn.toLowerCase().contains(q) || c.iso3.toLowerCase() == q)
        .toList();
    return Scaffold(
      appBar: AppBar(title: Text(widget.title)),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
            child: TextField(
              autofocus: true,
              decoration: const InputDecoration(prefixIcon: Icon(Icons.search), hintText: 'Qidirish (o\'zbekcha yoki inglizcha)'),
              onChanged: (v) => setState(() => query = v),
            ),
          ),
          Expanded(
            child: ListView.builder(
              itemCount: list.length,
              itemBuilder: (context, i) => ListTile(
                title: Text(list[i].name, style: TextStyle(color: t.ink)),
                subtitle: list[i].nameEn != list[i].name ? Text(list[i].nameEn, style: TextStyle(color: t.inkMuted)) : null,
                onTap: () => Navigator.of(context).pop(list[i].iso3),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  static const _thresholds = ['WATCH', 'ADVISORY', 'WARNING', 'EMERGENCY'];

  @override
  Widget build(BuildContext context) {
    final state = AppScope.of(context);
    final s = state.settings;
    final t = context.tokens;
    final catalog = state.catalog;
    return Scaffold(
      appBar: AppBar(title: const Text('Sozlamalar')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 32),
        children: [
          const SectionTitle('Joylashuv'),
          InfoCard(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: ListTile(
              leading: Icon(Icons.home_outlined, color: t.accentText),
              title: Text('Mening mamlakatim', style: TextStyle(color: t.ink)),
              subtitle: Text(catalog.countryName(s.country), style: TextStyle(color: t.inkMuted)),
              trailing: const Icon(Icons.chevron_right),
              onTap: () async {
                final c = await pickCountry(context);
                if (c != null) {
                  await state.updateSettings(s.copyWith(country: c, watchCountries: s.watchCountries.where((w) => w != c).toList()));
                }
              },
            ),
          ),
          const SizedBox(height: 4),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4),
            child: Text(
              "Joylashuv ruxsati so'ralmaydi: xavf mamlakatlar orasidagi masofa bo'yicha hisoblanadi.",
              style: TextStyle(color: t.inkMuted, fontSize: 12),
            ),
          ),
          SectionTitle(
            "Kuzatuv ro'yxati",
            trailing: TextButton.icon(
              onPressed: s.watchCountries.length >= 10
                  ? null
                  : () async {
                      final c = await pickCountry(context, title: "Kuzatuvga qo'shish", exclude: {s.country, ...s.watchCountries});
                      if (c != null) await state.updateSettings(s.copyWith(watchCountries: [...s.watchCountries, c]));
                    },
              icon: const Icon(Icons.add),
              label: const Text("Qo'shish"),
            ),
          ),
          InfoCard(
            child: s.watchCountries.isEmpty
                ? Text(
                    "Sayohat yo'nalishlaringiz yoki yaqinlaringiz yashaydigan mamlakatlarni qo'shing — u yerdagi "
                    "avj olishlar haqida ham xabar beriladi.",
                    style: TextStyle(color: t.inkMuted, height: 1.4),
                  )
                : Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      for (final w in s.watchCountries)
                        InputChip(
                          label: Text(catalog.countryName(w)),
                          onDeleted: () => state.updateSettings(s.copyWith(watchCountries: s.watchCountries.where((x) => x != w).toList())),
                          deleteButtonTooltipMessage: "O'chirish",
                        ),
                    ],
                  ),
          ),
          const SectionTitle('Ogohlantirishlar'),
          InfoCard(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Column(
              children: [
                SwitchListTile(
                  value: s.notificationsEnabled,
                  onChanged: (v) => state.updateSettings(s.copyWith(notificationsEnabled: v)),
                  title: Text('Push-bildirishnomalar', style: TextStyle(color: t.ink)),
                  subtitle: Text('Yangi yoki kuchaygan xavf haqida darhol xabar', style: TextStyle(color: t.inkMuted)),
                ),
                if (s.notificationsEnabled && state.notificationStatus != 'granted')
                  ListTile(
                    leading: Icon(Icons.notifications_off_outlined, color: t.warn),
                    title: Text('Tizim bildirishnomalarga ruxsat bermagan', style: TextStyle(color: t.ink)),
                    trailing: TextButton(
                      onPressed: () async {
                        final r = await state.requestNotifications();
                        if (r != 'granted') await state.engine.openNotificationSettings();
                      },
                      child: const Text('Ruxsat berish'),
                    ),
                  ),
              ],
            ),
          ),
          const SectionTitle('Qaysi darajadan xabar berilsin'),
          InfoCard(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: RadioGroup<String>(
              groupValue: s.alertThreshold,
              onChanged: (v) => v == null ? null : state.updateSettings(s.copyWith(alertThreshold: v)),
              child: Column(
                children: [
                  for (final l in _thresholds)
                    RadioListTile<String>(
                      value: l,
                      title: Text('${catalog.level(l)?.name ?? l} va undan yuqori', style: TextStyle(color: t.ink)),
                      subtitle: Text('${catalog.level(l)?.minScore ?? ''}+ ball', style: TextStyle(color: t.inkMuted)),
                      secondary: Icon(Icons.circle, size: 14, color: context.levelColor(l)),
                    ),
                ],
              ),
            ),
          ),
          const SectionTitle('Yangilash chastotasi'),
          InfoCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    for (final h in Settings.syncChoices)
                      ChoiceChip(
                        label: Text('$h soat'),
                        selected: s.syncHours == h,
                        onSelected: (_) => state.updateSettings(s.copyWith(syncHours: h)),
                      ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  state.lastSync == null ? "Hali yangilanmagan" : 'Oxirgi yangilanish: ${formatDateTime(state.lastSync!)}',
                  style: TextStyle(color: t.inkMuted, fontSize: 12),
                ),
              ],
            ),
          ),
          const SectionTitle("Ko'rinish"),
          InfoCard(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: SwitchListTile(
              value: s.lightTheme,
              onChanged: (v) => state.updateSettings(s.copyWith(lightTheme: v)),
              title: Text("Yorug' mavzu", style: TextStyle(color: t.ink)),
              subtitle: Text("Standart — qorong'i mavzu", style: TextStyle(color: t.inkMuted)),
            ),
          ),
          const SectionTitle("Ma'lumot manbalari"),
          InfoCard(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Column(
              children: [
                for (final src in state.snapshot?.sources ?? const <SourceStatus>[])
                  ListTile(
                    title: Text(src.title, style: TextStyle(color: t.ink)),
                    subtitle: Text(src.homepage, style: TextStyle(color: t.inkMuted, fontSize: 12)),
                    trailing: const Icon(Icons.open_in_new, size: 18),
                    onTap: () => state.engine.openUrl(src.homepage),
                  ),
              ],
            ),
          ),
          const SectionTitle('Ilova haqida'),
          InfoCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  "EpiRadar faqat ochiq rasmiy manbalarni (JSST, ECDC, CDC) tahlil qiladi, shaxsiy ma'lumot yig'maydi "
                  "va hech qayerga yubormaydi. Tahlil to'liq qurilmaning o'zida bajariladi.",
                  style: TextStyle(color: t.ink, height: 1.4),
                ),
                const SizedBox(height: 8),
                Text(
                  "Mamlakatlar ma'lumoti: mledoze/countries (ODbL 1.0). Shrift: Noto Sans (SIL OFL 1.1).",
                  style: TextStyle(color: t.inkMuted, fontSize: 12),
                ),
                const MedicalDisclaimer(),
                OutlinedButton(
                  onPressed: () => showLicensePage(context: context, applicationName: 'EpiRadar'),
                  child: const Text('Litsenziyalar'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
