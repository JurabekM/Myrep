import 'package:flutter/material.dart';

import '../data/models.dart';
import '../state/app_state.dart';
import '../theme.dart';
import '../util/format.dart';
import 'settings_screen.dart';
import 'widgets.dart';

/// Gripp laboratoriya kuzatuvi trendlari va g'ayritabiiy o'sish (aberration) signallari.
class TrendsScreen extends StatelessWidget {
  const TrendsScreen({super.key});

  static String statusLevel(String status) => switch (status) {
        'UNUSUAL' => 'WARNING',
        'RISING' => 'ADVISORY',
        'NORMAL' => 'CALM',
        _ => 'WATCH',
      };

  @override
  Widget build(BuildContext context) {
    final state = AppScope.of(context);
    final t = context.tokens;
    final trends = [...?state.snapshot?.trends]..sort((a, b) {
        int rank(Trend x) => x.country == state.settings.country ? 0 : (x.status == 'NO_DATA' ? 2 : 1);
        return rank(a).compareTo(rank(b));
      });
    return Scaffold(
      appBar: AppBar(title: const Text('Trendlar'), actions: const [SettingsButton()]),
      body: RefreshIndicator(
        onRefresh: state.refresh,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 4, 16, 32),
          children: [
            Text(
              "JSST FluNet laboratoriya ma'lumotlari: tekshirilgan namunalarning necha foizida gripp virusi topilgani. "
              "Qizil nuqta — statistik jihatdan g'ayritabiiy o'sish.",
              style: TextStyle(color: t.inkMuted, height: 1.4),
            ),
            const SizedBox(height: 12),
            if (trends.isEmpty)
              const EmptyState(icon: Icons.show_chart, title: "Trend ma'lumotlari hali yuklanmagan")
            else
              for (final tr in trends) ...[
                _TrendCard(trend: tr),
                const SizedBox(height: 12),
              ],
            const SectionTitle('Usul haqida'),
            InfoCard(
              child: Text(
                "• EARS C2 (AQSh CDC): joriy hafta 2 haftalik tanaffusdan oldingi 7 haftaga solishtiriladi; "
                "o'sish 3 standart chetlanishdan katta bo'lsa — «O'sish kuzatilmoqda».\n"
                "• Tarixiy chegara (Stroup, 1989): joriy qiymat o'tgan 3 yilning shu davri (±2 hafta) bilan "
                "solishtiriladi; o'rtacha + 2σ dan yuqori bo'lsa — «Mavsum me'yoridan yuqori». Shu tufayli "
                "har qishdagi odatiy gripp mavsumi yolg'on signal bermaydi.\n"
                "• Odam namunasida A(H5) yoki A(H7N9) qush grippi topilsa — alohida ogohlantirish.",
                style: TextStyle(color: t.ink, height: 1.45),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _TrendCard extends StatelessWidget {
  const _TrendCard({required this.trend});

  final Trend trend;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final level = TrendsScreen.statusLevel(trend.status);
    final c = context.levelColor(level);
    final engine = AppScope.read(context).engine;
    return InfoCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(child: Text(trend.countryName, style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: t.ink))),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: c.withValues(alpha: 0.14),
                  borderRadius: BorderRadius.circular(999),
                  border: Border.all(color: c.withValues(alpha: 0.6)),
                ),
                child: Text(trend.statusName, style: TextStyle(color: c, fontWeight: FontWeight.w700, fontSize: 12)),
              ),
            ],
          ),
          if (trend.novelFluWeeks.isNotEmpty) ...[
            const SizedBox(height: 10),
            Row(
              children: [
                Icon(Icons.warning_amber_rounded, color: t.danger),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Odam namunasida qush grippi: ${trend.novelFluWeeks.map((w) => formatShortDate(DateTime.parse(w))).join(', ')} haftalari',
                    style: TextStyle(color: t.danger, fontWeight: FontWeight.w700),
                  ),
                ),
              ],
            ),
          ],
          const SizedBox(height: 12),
          TrendChart(trend: trend),
          const SizedBox(height: 10),
          Text(trend.note, style: TextStyle(color: t.ink, height: 1.4)),
          if (trend.anomalies.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              '${trend.anomalies.length} ta signal: ${trend.anomalies.reversed.take(3).map((a) => '${formatShortDate(a.week)} ${formatPercent(a.value)} (${a.method})').join('; ')}',
              style: TextStyle(color: t.inkMuted, fontSize: 12),
            ),
          ],
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(onPressed: () => engine.openUrl('https://www.who.int/tools/flunet'), child: const Text('JSST FluNet')),
          ),
        ],
      ),
    );
  }
}
