import 'package:flutter/material.dart';

import '../state/app_state.dart';
import '../theme.dart';
import 'cards.dart';
import 'charts.dart';
import 'widgets.dart';

/// 7 kunlik prognoz va keyingi 48 soat grafigi.
class ForecastScreen extends StatelessWidget {
  const ForecastScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final state = AppScope.of(context);
    final place = state.viewed;
    final t = context.tokens;
    return Scaffold(
      appBar: AppBar(title: Text(place == null ? 'Prognoz' : 'Prognoz · ${place.name}')),
      body: place == null || place.days.isEmpty
          ? const EmptyState(icon: Icons.calendar_month_outlined, title: "Prognoz hali yuklanmagan")
          : ListView(
              padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
              children: [
                if (state.snapshot != null) PlaceChips(snapshot: state.snapshot!),
                const SectionTitle('Keyingi 48 soat'),
                InfoCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Issiqlik ko\'rsatkichi va harorat', style: TextStyle(color: t.inkMuted, fontSize: 12)),
                      const SizedBox(height: 6),
                      TempChart(hours: place.hours),
                      if (place.hours.any((h) => h.pm25 != null)) ...[
                        const SizedBox(height: 14),
                        Text('PM2.5, µg/m³ (chiziq — JSST tavsiyasi)', style: TextStyle(color: t.inkMuted, fontSize: 12)),
                        const SizedBox(height: 6),
                        Pm25Chart(hours: place.hours),
                      ],
                    ],
                  ),
                ),
                const SectionTitle('Kunlar'),
                for (final d in place.days) ...[DayRow(day: d, place: place), const SizedBox(height: 8)],
                Text(
                  "Havo sifati prognozi 5 kungacha (Copernicus CAMS); oxirgi kunlarda faqat issiqlik baholanadi.",
                  style: TextStyle(color: t.inkMuted, fontSize: 12),
                ),
              ],
            ),
    );
  }
}
