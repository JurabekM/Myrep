import 'package:flutter/material.dart';

import '../data/models.dart';
import '../state/app_state.dart';
import '../theme.dart';
import '../util/format.dart';
import 'day_screen.dart';
import 'widgets.dart';

IconData hazardIcon(String hazard) => hazard == 'HEAT' ? Icons.thermostat : Icons.air;

/// Bir xavf kartasi: daraja, asosiy ko'rsatkich va birinchi sabab. Bosilsa — kun tafsiloti.
class HazardTile extends StatelessWidget {
  const HazardTile({super.key, required this.risk, required this.day, required this.place});

  final HazardRisk risk;
  final DayReport day;
  final PlaceReport place;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final color = context.levelColor(risk.personal.level);
    final metric = risk.isHeat
        ? [
            if (day.tempMax != null) 'Eng yuqori ${deg(day.tempMax)}C',
            if (day.feelsMax != null && (day.feelsMax! - (day.tempMax ?? 0)) >= 1) 'his qilinadi ${deg(day.feelsMax)}C',
            if (day.feelsPeakHour != null) '${hourLabel(day.feelsPeakHour!)} atrofida',
          ].join(' · ')
        : [
            if (day.air?.pm25 != null) 'PM2.5 ${num0(day.air!.pm25)} µg/m³',
            if (day.air?.pm10 != null) 'PM10 ${num0(day.air!.pm10)}',
          ].join(' · ');
    return InfoCard(
      padding: EdgeInsets.zero,
      onTap: () => Navigator.of(context).push(
        MaterialPageRoute<void>(builder: (_) => DayScreen(placeId: place.id, date: day.date)),
      ),
      child: IntrinsicHeight(
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Container(width: 5, color: color),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(hazardIcon(risk.hazard), color: color, size: 20),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(risk.name, style: TextStyle(fontWeight: FontWeight.w700, color: t.ink, fontSize: 15)),
                        ),
                        LevelBadge(risk.personal),
                      ],
                    ),
                    if (metric.isNotEmpty) ...[
                      const SizedBox(height: 6),
                      Text(metric, style: TextStyle(color: t.ink)),
                    ],
                    if (risk.reasons.isNotEmpty) ...[
                      const SizedBox(height: 4),
                      Text(risk.reasons.first, style: TextStyle(color: t.inkMuted, fontSize: 13, height: 1.35)),
                    ],
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Prognoz ro'yxatidagi bitta kun.
class DayRow extends StatelessWidget {
  const DayRow({super.key, required this.day, required this.place});

  final DayReport day;
  final PlaceReport place;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final overall = day.overall;
    return InfoCard(
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
      onTap: () => Navigator.of(context).push(
        MaterialPageRoute<void>(builder: (_) => DayScreen(placeId: place.id, date: day.date)),
      ),
      child: Row(
        children: [
          SizedBox(
            width: 92,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(dayLabel(day.date, place.localNow), style: TextStyle(fontWeight: FontWeight.w700, color: t.ink)),
                Text(formatShortDate(day.date), style: TextStyle(color: t.inkMuted, fontSize: 12)),
              ],
            ),
          ),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  day.tempMax == null ? "Harorat ma'lumoti yo'q" : '${deg(day.tempMin)} / ${deg(day.tempMax)}',
                  style: TextStyle(color: t.ink, fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 2),
                Text(
                  [
                    if (day.air?.pm25 != null) 'PM2.5 ${num0(day.air!.pm25)}',
                    if (day.uvMax != null) 'UV ${num0(day.uvMax)}',
                  ].join(' · '),
                  style: TextStyle(color: t.inkMuted, fontSize: 12),
                ),
              ],
            ),
          ),
          if (overall != null) LevelBadge(overall) else Text('—', style: TextStyle(color: t.inkMuted)),
        ],
      ),
    );
  }
}

/// Hozirgi soat: harorat, issiqlik ko'rsatkichi, PM2.5, UV.
class CurrentStrip extends StatelessWidget {
  const CurrentStrip({super.key, required this.hour});

  final HourPoint hour;

  @override
  Widget build(BuildContext context) {
    Widget cell(String label, String value) {
      final t = context.tokens;
      return Expanded(
        child: Column(
          children: [
            Text(value, style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700, color: t.ink)),
            const SizedBox(height: 2),
            Text(label, textAlign: TextAlign.center, style: TextStyle(fontSize: 12, color: t.inkMuted)),
          ],
        ),
      );
    }

    return InfoCard(
      padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 8),
      child: Row(
        children: [
          cell('Harorat', '${deg(hour.temp)}C'),
          cell('His qilinadi', '${deg(hour.feels)}C'),
          cell('PM2.5', num0(hour.pm25)),
          cell('UV', num0(hour.uv)),
        ],
      ),
    );
  }
}

/// Joylar o'rtasida almashish (asosiy + qo'shimcha joylar).
class PlaceChips extends StatelessWidget {
  const PlaceChips({super.key, required this.snapshot});

  final Snapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final state = AppScope.of(context);
    final current = state.viewed?.id;
    if (snapshot.places.length < 2) return const SizedBox.shrink();
    return SizedBox(
      height: 44,
      child: ListView(
        scrollDirection: Axis.horizontal,
        children: [
          for (final p in snapshot.places)
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: ChoiceChip(
                label: Text(p.today == null ? p.name : '${p.name} · ${p.today!.score}'),
                selected: p.id == current,
                onSelected: (_) => state.viewPlace(p.id),
              ),
            ),
        ],
      ),
    );
  }
}
