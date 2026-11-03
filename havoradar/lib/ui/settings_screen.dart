import 'package:flutter/material.dart';

import '../data/models.dart';
import '../state/app_state.dart';
import '../theme.dart';
import 'widgets.dart';

/// Play Console'da ham shu havola ko'rsatiladi (docs/PRIVACY.md).
const privacyPolicyUrl = 'https://github.com/JurabekM/Myrep/blob/master/havoradar/docs/PRIVACY.md';

/// Joy tanlash (qidiruvli). Tanlangan joy id'si yoki null qaytaradi.
Future<String?> pickPlace(BuildContext context, {String title = 'Shaharni tanlang', Set<String> exclude = const {}}) =>
    Navigator.of(context).push<String>(
      MaterialPageRoute(fullscreenDialog: true, builder: (_) => _PlacePicker(title: title, exclude: exclude)),
    );

class _PlacePicker extends StatefulWidget {
  const _PlacePicker({required this.title, required this.exclude});

  final String title;
  final Set<String> exclude;

  @override
  State<_PlacePicker> createState() => _PlacePickerState();
}

class _PlacePickerState extends State<_PlacePicker> {
  String query = '';

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final q = query.trim().toLowerCase();
    final list = AppScope.of(context)
        .catalog
        .places
        .where((p) => !widget.exclude.contains(p.id))
        .where((p) => q.isEmpty || p.name.toLowerCase().contains(q) || p.id.contains(q))
        .toList();
    final home = list.where((p) => !p.abroad).toList();
    final abroad = list.where((p) => p.abroad).toList();
    Widget header(String s) => Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 4),
          child: Text(s, style: TextStyle(color: t.inkMuted, fontWeight: FontWeight.w700, fontSize: 13)),
        );
    Widget tile(PlaceInfo p) => ListTile(
          title: Text(p.name, style: TextStyle(color: t.ink)),
          onTap: () => Navigator.of(context).pop(p.id),
        );
    return Scaffold(
      appBar: AppBar(title: Text(widget.title)),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
            child: TextField(
              decoration: const InputDecoration(prefixIcon: Icon(Icons.search), hintText: 'Qidirish'),
              onChanged: (v) => setState(() => query = v),
            ),
          ),
          Expanded(
            child: ListView(
              children: [
                if (home.isNotEmpty) header("O'zbekiston"),
                ...home.map(tile),
                if (abroad.isNotEmpty) header('Xorij (qarindoshlar, ish, ziyorat)'),
                ...abroad.map(tile),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// Sezgir guruhlar tanlovi (onboarding va sozlamalarda bir xil).
class ProfilePicker extends StatelessWidget {
  const ProfilePicker({super.key});

  @override
  Widget build(BuildContext context) {
    final state = AppScope.of(context);
    final t = context.tokens;
    final s = state.settings;
    return Column(
      children: [
        for (final v in state.catalog.vulnerabilities)
          CheckboxListTile(
            contentPadding: EdgeInsets.zero,
            controlAffinity: ListTileControlAffinity.leading,
            value: s.profile.contains(v.id),
            title: Text(v.name, style: TextStyle(color: t.ink)),
            subtitle: Text(
              [if (v.heat) 'issiqlik', if (v.air) 'havo ifloslanishi'].join(' va '),
              style: TextStyle(color: t.inkMuted, fontSize: 12),
            ),
            onChanged: (on) {
              final next = s.profile.where((p) => p != v.id).toList();
              if (on ?? false) next.add(v.id);
              state.updateSettings(s.copyWith(profile: next));
            },
          ),
      ],
    );
  }
}

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final state = AppScope.of(context);
    final t = context.tokens;
    final s = state.settings;
    final catalog = state.catalog;
    return Scaffold(
      appBar: AppBar(title: const Text('Sozlamalar')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
        children: [
          const SectionTitle('Asosiy joy'),
          InfoCard(
            padding: EdgeInsets.zero,
            child: ListTile(
              leading: Icon(Icons.location_city, color: t.accentText),
              title: Text(catalog.placeName(s.placeId), style: TextStyle(color: t.ink)),
              subtitle: Text("GPS ishlatilmaydi — shahar ro'yxatdan tanlanadi", style: TextStyle(color: t.inkMuted)),
              trailing: const Icon(Icons.chevron_right),
              onTap: () async {
                final id = await pickPlace(context, exclude: {s.placeId});
                if (id != null) {
                  await state.updateSettings(s.copyWith(placeId: id, extraPlaces: s.extraPlaces.where((p) => p != id).toList()));
                }
              },
            ),
          ),
          SectionTitle(
            "Qo'shimcha joylar (${s.extraPlaces.length}/${Settings.maxExtraPlaces})",
            trailing: s.extraPlaces.length < Settings.maxExtraPlaces
                ? TextButton.icon(
                    onPressed: () async {
                      final id = await pickPlace(context, title: "Joy qo'shish", exclude: s.allPlaces.toSet());
                      if (id != null) await state.updateSettings(s.copyWith(extraPlaces: [...s.extraPlaces, id]));
                    },
                    icon: const Icon(Icons.add),
                    label: const Text("Qo'shish"),
                  )
                : null,
          ),
          if (s.extraPlaces.isEmpty)
            Text(
              "Ota-onangiz, qarindoshlaringiz yashaydigan yoki safarga boradigan joyingizni qo'shing — u yerdagi xavf haqida ham xabar beriladi.",
              style: TextStyle(color: t.inkMuted, height: 1.4),
            )
          else
            InfoCard(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Column(
                children: [
                  for (final id in s.extraPlaces)
                    ListTile(
                      title: Text(catalog.placeName(id), style: TextStyle(color: t.ink)),
                      trailing: IconButton(
                        tooltip: "Olib tashlash",
                        icon: const Icon(Icons.close),
                        onPressed: () => state.updateSettings(s.copyWith(extraPlaces: s.extraPlaces.where((p) => p != id).toList())),
                      ),
                    ),
                ],
              ),
            ),
          const SectionTitle('Sezgir guruhlar'),
          Text(
            "Siz yoki oilangizda bo'lsa belgilang: ogohlantirish ertaroq keladi (ball 25% yuqori). Ma'lumot faqat telefoningizda saqlanadi.",
            style: TextStyle(color: t.inkMuted, height: 1.4),
          ),
          const ProfilePicker(),
          const SectionTitle('Bildirishnomalar'),
          InfoCard(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Column(
              children: [
                SwitchListTile(
                  title: Text('Ogohlantirishlar', style: TextStyle(color: t.ink)),
                  subtitle: Text(_permissionText(state.notificationStatus), style: TextStyle(color: t.inkMuted)),
                  value: s.notificationsEnabled,
                  onChanged: (v) async {
                    if (v && state.notificationStatus != 'granted') {
                      final r = await state.requestNotifications();
                      if (r != 'granted') await state.engine.openNotificationSettings();
                    }
                    await state.updateSettings(s.copyWith(notificationsEnabled: v));
                  },
                ),
                SwitchListTile(
                  title: Text('Tungi sokin soatlar (22:00–07:00)', style: TextStyle(color: t.ink)),
                  subtitle: Text("Tunda faqat «Favqulodda» xabar beriladi, qolganlari ertalab", style: TextStyle(color: t.inkMuted)),
                  value: s.quietHours,
                  onChanged: (v) => state.updateSettings(s.copyWith(quietHours: v)),
                ),
              ],
            ),
          ),
          const SectionTitle('Qaysi darajadan xabar berilsin'),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final l in catalog.levels.where((l) => l.level != 'CALM'))
                ChoiceChip(
                  label: Text(l.name),
                  selected: s.alertThreshold == l.level,
                  onSelected: (_) => state.updateSettings(s.copyWith(alertThreshold: l.level)),
                ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            "Tavsiya — «Xavfli»: yozda «Ehtiyot» darajasi deyarli har kuni bo'ladi.",
            style: TextStyle(color: t.inkMuted, fontSize: 12),
          ),
          const SectionTitle('Yangilash chastotasi'),
          Wrap(
            spacing: 8,
            children: [
              for (final h in Settings.syncChoices)
                ChoiceChip(
                  label: Text('$h soat'),
                  selected: s.syncHours == h,
                  onSelected: (_) => state.updateSettings(s.copyWith(syncHours: h)),
                ),
            ],
          ),
          const SectionTitle("Ko'rinish"),
          InfoCard(
            padding: EdgeInsets.zero,
            child: SwitchListTile(
              title: Text("Yorug' mavzu", style: TextStyle(color: t.ink)),
              subtitle: Text("Standart — qorong'i", style: TextStyle(color: t.inkMuted)),
              value: s.lightTheme,
              onChanged: (v) => state.updateSettings(s.copyWith(lightTheme: v)),
            ),
          ),
          const SectionTitle('Ilova haqida'),
          Text(
            "Prognoz: Open-Meteo.com (CC BY 4.0) — milliy meteorologiya xizmatlari modellari va Copernicus CAMS. "
            "Baholash: NWS issiqlik indeksi, JSST 2021 havo sifati tavsiyalari. Shaxsiy ma'lumot yig'ilmaydi.",
            style: TextStyle(color: t.inkMuted, height: 1.4),
          ),
          TextButton(
            style: TextButton.styleFrom(alignment: Alignment.centerLeft, padding: EdgeInsets.zero),
            onPressed: () => state.engine.openUrl(privacyPolicyUrl),
            child: const Text('Maxfiylik siyosati'),
          ),
          const MedicalDisclaimer(),
        ],
      ),
    );
  }

  static String _permissionText(String status) => switch (status) {
        'granted' => "Ruxsat berilgan",
        'denied' => "Ruxsat berilmagan — yoqish uchun bosing",
        _ => "Tizim sozlamalarida o'chirilgan",
      };
}
