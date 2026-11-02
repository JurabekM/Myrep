import 'package:flutter/material.dart';

import '../data/models.dart';
import '../state/app_state.dart';
import '../theme.dart';
import '../util/format.dart';
import 'cards.dart';
import 'charts.dart';
import 'widgets.dart';

/// Bir kun tafsiloti: soatlik grafiklar, har bir xavf bo'yicha «Nega bu daraja?» va tavsiyalar.
class DayScreen extends StatelessWidget {
  const DayScreen({super.key, required this.placeId, required this.date});

  final String placeId;
  final DateTime date;

  @override
  Widget build(BuildContext context) {
    final state = AppScope.of(context);
    final t = context.tokens;
    final place = state.snapshot?.place(placeId);
    DayReport? day;
    for (final d in place?.days ?? const <DayReport>[]) {
      if (d.date == date) day = d;
    }
    if (place == null || day == null) {
      return Scaffold(
        appBar: AppBar(),
        body: const EmptyState(icon: Icons.event_busy, title: "Bu kun uchun ma'lumot yo'q"),
      );
    }
    final d = day;
    final hours = place.hoursOn(date);
    return Scaffold(
      appBar: AppBar(title: Text('${place.name} · ${dayLabel(date, place.localNow).toLowerCase()}')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
        children: [
          Text(formatDate(date), style: TextStyle(color: t.inkMuted)),
          const SizedBox(height: 8),
          if (d.overall != null)
            Wrap(
              spacing: 10,
              runSpacing: 6,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                LevelBadge(d.overall!, prefix: 'Umumiy'),
                if (d.tempMax != null) Text('${deg(d.tempMin)} / ${deg(d.tempMax)}', style: TextStyle(color: t.ink, fontWeight: FontWeight.w700)),
              ],
            ),
          if (hours.length >= 2) ...[
            const SectionTitle('Harorat (soatlik)'),
            InfoCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  TempChart(hours: hours),
                  const SizedBox(height: 8),
                  _Legend(items: [
                    (t.accent, 'Issiqlik ko\'rsatkichi'),
                    (t.inkMuted, 'Havo harorati'),
                    (context.levelColor('WARNING'), 'NWS «Xavf» chegarasi 39,4°'),
                  ]),
                ],
              ),
            ),
            if (hours.any((h) => h.pm25 != null)) ...[
              const SectionTitle('PM2.5 (soatlik, µg/m³)'),
              InfoCard(child: Pm25Chart(hours: hours)),
            ],
          ],
          for (final r in d.risks) _HazardSection(risk: r, day: d),
          if (d.uv != null) ...[
            const SectionTitle('Quyosh nurlari'),
            InfoCard(
              child: Text('UV indeksi ${num0(d.uvMax)} — ${d.uv!.name}. ${d.uv!.advice}', style: TextStyle(color: t.ink, height: 1.4)),
            ),
          ],
          const SizedBox(height: 12),
          OutlinedButton.icon(
            onPressed: () => state.engine.share(_shareText(place, d)),
            icon: const Icon(Icons.share_outlined),
            label: const Text('Yaqinlarga ulashish'),
          ),
          const MedicalDisclaimer(),
        ],
      ),
    );
  }

  static String _shareText(PlaceReport place, DayReport d) {
    final lines = <String>[
      '${place.name}, ${formatShortDate(d.date)}:',
      if (d.tempMax != null) 'Harorat ${deg(d.tempMin)}…${deg(d.tempMax)}C',
      for (final r in d.risks) '${r.name}: ${r.base.name} (${r.base.score}/100)',
      for (final r in d.risks) ...r.advice.take(2),
      '— HavoRadar (JSST/CDC tavsiyalari asosida)',
    ];
    return lines.join('\n');
  }
}

class _HazardSection extends StatelessWidget {
  const _HazardSection({required this.risk, required this.day});

  final HazardRisk risk;
  final DayReport day;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final color = context.levelColor(risk.personal.level);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SectionTitle(risk.name, trailing: LevelBadge(risk.personal)),
        InfoCard(
          borderColor: color.withValues(alpha: 0.6),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(hazardIcon(risk.hazard), color: color),
                  const SizedBox(width: 8),
                  Expanded(child: Text('Nega bu daraja?', style: TextStyle(fontWeight: FontWeight.w700, color: t.ink))),
                ],
              ),
              const SizedBox(height: 8),
              BulletList(risk.reasons, color: color),
              if (risk.personal.score != risk.base.score)
                Text(
                  'Umumiy aholi uchun: ${risk.base.name} (${risk.base.score}). Siz uchun: ${risk.personal.name} (${risk.personal.score}).',
                  style: TextStyle(color: t.inkMuted, fontSize: 12),
                ),
              if (risk.advice.isNotEmpty) ...[
                const SizedBox(height: 12),
                Text('Nima qilish kerak', style: TextStyle(fontWeight: FontWeight.w700, color: t.ink)),
                const SizedBox(height: 8),
                BulletList(risk.advice),
              ],
            ],
          ),
        ),
      ],
    );
  }
}

class _Legend extends StatelessWidget {
  const _Legend({required this.items});

  final List<(Color, String)> items;

  @override
  Widget build(BuildContext context) => Wrap(
        spacing: 14,
        runSpacing: 4,
        children: [
          for (final (color, label) in items)
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(width: 14, height: 3, color: color),
                const SizedBox(width: 6),
                Flexible(child: Text(label, style: TextStyle(color: context.tokens.inkMuted, fontSize: 12))),
              ],
            ),
        ],
      );
}
