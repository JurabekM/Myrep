import 'package:flutter/material.dart';

import '../data/models.dart';
import '../state/app_state.dart';
import '../theme.dart';
import '../util/format.dart';
import 'cards.dart';
import 'settings_screen.dart';
import 'widgets.dart';

/// Radar: tanlangan joy uchun bugungi umumiy xavf, hozirgi ko'rsatkichlar, issiqlik va havo kartalari.
class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key, required this.onShowForecast});

  final VoidCallback onShowForecast;

  @override
  Widget build(BuildContext context) {
    final state = AppScope.of(context);
    final snap = state.snapshot;
    final place = state.viewed;
    final t = context.tokens;
    return Scaffold(
      appBar: AppBar(
        title: Text(place?.name ?? state.catalog.placeName(state.settings.placeId)),
        actions: [
          IconButton(
            tooltip: 'Yangilash',
            onPressed: state.refreshing ? null : state.refresh,
            icon: state.refreshing
                ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                : const Icon(Icons.refresh),
          ),
          IconButton(
            tooltip: 'Sozlamalar',
            onPressed: () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const SettingsScreen())),
            icon: const Icon(Icons.settings_outlined),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: state.refresh,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
          children: [
            if (state.error != null) _ErrorBanner(state.error!),
            if (snap == null || place == null)
              _FirstLoad(refreshing: state.refreshing, onRetry: state.refresh)
            else ...[
              PlaceChips(snapshot: snap),
              _TodayHeader(place: place),
              if (place.current != null) ...[const SizedBox(height: 12), CurrentStrip(hour: place.current!)],
              ..._todayCards(context, place),
              _Tomorrow(place: place, onTap: onShowForecast),
              const SectionTitle("Shoshilinch yordam"),
              const _EmergencyCard(),
              const SectionTitle("Ma'lumot manbalari"),
              _SourcesCard(snapshot: snap),
              const SizedBox(height: 8),
              Text(
                state.lastSync == null ? '' : 'Oxirgi yangilanish: ${timeAgo(state.lastSync!)}',
                style: TextStyle(color: t.inkMuted, fontSize: 12),
              ),
              const MedicalDisclaimer(),
            ],
          ],
        ),
      ),
    );
  }

  List<Widget> _todayCards(BuildContext context, PlaceReport place) {
    final today = place.todayReport;
    if (today == null) {
      return const [
        SizedBox(height: 16),
        EmptyState(icon: Icons.cloud_off, title: "Bugun uchun prognoz yo'q", message: 'Internetga ulaning va yangilang.'),
      ];
    }
    return [
      const SectionTitle('Bugun'),
      for (final r in today.risks) ...[HazardTile(risk: r, day: today, place: place), const SizedBox(height: 10)],
      if (today.uv != null) _UvCard(day: today),
    ];
  }
}

class _TodayHeader extends StatelessWidget {
  const _TodayHeader({required this.place});

  final PlaceReport place;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final level = place.today;
    if (level == null) return const SizedBox(height: 8);
    final state = AppScope.read(context);
    final personal = state.settings.profile.isNotEmpty;
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: InfoCard(
        onTap: () => showLevelsSheet(context),
        child: Column(
          children: [
            ScoreGauge(level: level),
            const SizedBox(height: 8),
            Text(
              personal ? 'Bugungi xavf — profilingiz hisobga olingan' : 'Bugungi umumiy xavf',
              style: TextStyle(color: t.inkMuted, fontSize: 12),
            ),
            const SizedBox(height: 6),
            Text(level.advice, textAlign: TextAlign.center, style: TextStyle(color: t.ink, height: 1.4)),
          ],
        ),
      ),
    );
  }
}

class _UvCard extends StatelessWidget {
  const _UvCard({required this.day});

  final DayReport day;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final uv = day.uv!;
    final level = switch (uv.category) {
      'LOW' => 'CALM',
      'MODERATE' => 'WATCH',
      'HIGH' => 'ADVISORY',
      'VERY_HIGH' => 'WARNING',
      _ => 'EMERGENCY',
    };
    final color = context.levelColor(level);
    return InfoCard(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.wb_sunny_outlined, color: color),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('UV indeksi ${num0(day.uvMax)} — ${uv.name}', style: TextStyle(fontWeight: FontWeight.w700, color: t.ink)),
                const SizedBox(height: 4),
                Text(uv.advice, style: TextStyle(color: t.inkMuted, fontSize: 13, height: 1.35)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _Tomorrow extends StatelessWidget {
  const _Tomorrow({required this.place, required this.onTap});

  final PlaceReport place;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final today = place.todayReport;
    final i = today == null ? -1 : place.days.indexOf(today);
    final next = i >= 0 && i + 1 < place.days.length ? place.days[i + 1] : null;
    if (next == null) return const SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SectionTitle('Ertaga', trailing: TextButton(onPressed: onTap, child: const Text('7 kunlik prognoz'))),
        DayRow(day: next, place: place),
        if (next.overall != null && today?.overall != null && next.overall!.rank > today!.overall!.rank)
          Padding(
            padding: const EdgeInsets.only(top: 6, left: 4),
            child: Text('Ertaga xavf kuchayadi — oldindan tayyorlaning.', style: TextStyle(color: t.warn, fontSize: 13)),
          ),
      ],
    );
  }
}

void showLevelsSheet(BuildContext context) {
  final catalog = AppScope.read(context).catalog;
  showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    builder: (context) {
      final t = context.tokens;
      return SafeArea(
        child: ListView(
          shrinkWrap: true,
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
          children: [
            Text('Xavf darajalari', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: t.ink)),
            const SizedBox(height: 6),
            Text(
              "Ball 0–100. Issiqlik — AQSh Milliy ob-havo xizmati (NWS) issiqlik indeksi toifalari, tropik tunlar va "
              "ketma-ket issiq kunlar. Havo — JSST 2021 havo sifati tavsiyalari (PM2.5, PM10, ozon, NO₂). "
              "Kunning umumiy darajasi — ikkalasining yomonrog'i. Sezgir guruhlar uchun ball 25% yuqori.",
              style: TextStyle(color: t.inkMuted, height: 1.4),
            ),
            const SizedBox(height: 12),
            for (final l in catalog.levels)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SizedBox(
                      width: 104,
                      child: LevelBadge(Level(score: l.minScore, level: l.level, name: l.name, advice: l.advice), showScore: false),
                    ),
                    const SizedBox(width: 8),
                    Expanded(child: Text('${l.minScore}+ ball. ${l.advice}', style: TextStyle(color: t.ink, height: 1.35))),
                  ],
                ),
              ),
          ],
        ),
      );
    },
  );
}

class _EmergencyCard extends StatelessWidget {
  const _EmergencyCard();

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final state = AppScope.read(context);
    return InfoCard(
      child: Row(
        children: [
          Icon(Icons.local_hospital_outlined, color: t.danger, size: 32),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Tez tibbiy yordam — 103', style: TextStyle(fontWeight: FontWeight.w700, color: t.ink)),
                const SizedBox(height: 2),
                Text(
                  "Chalkashlik, hushdan ketish, tutqanoq yoki juda yuqori harorat — issiq urishi belgisi bo'lishi mumkin.",
                  style: TextStyle(color: t.inkMuted, fontSize: 13),
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          FilledButton(
            onPressed: () => state.engine.dial('103'),
            style: FilledButton.styleFrom(minimumSize: const Size(56, 56), padding: const EdgeInsets.symmetric(horizontal: 16)),
            child: const Icon(Icons.call, semanticLabel: "103 ga qo'ng'iroq"),
          ),
        ],
      ),
    );
  }
}

class _SourcesCard extends StatelessWidget {
  const _SourcesCard({required this.snapshot});

  final Snapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final state = AppScope.read(context);
    return InfoCard(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Column(
        children: [
          for (final s in snapshot.sources)
            ListTile(
              dense: true,
              onTap: s.homepage.isEmpty ? null : () => state.engine.openUrl(s.homepage),
              leading: Icon(
                s.ok ? Icons.cloud_done_outlined : (s.stale ? Icons.cloud_off_outlined : Icons.error_outline),
                color: s.ok ? context.levelColor('CALM') : (s.stale ? t.warn : t.danger),
              ),
              title: Text(s.title, style: TextStyle(color: t.ink)),
              subtitle: Text(
                s.ok
                    ? 'Yangilangan: ${s.fetchedAt == null ? '—' : timeAgo(s.fetchedAt!)}'
                    : '${s.error ?? 'Xato'}${s.stale ? " — oxirgi saqlangan prognoz ishlatilmoqda" : ''}',
                style: TextStyle(color: t.inkMuted),
              ),
            ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
            child: Text(
              "Ma'lumotlar: Open-Meteo.com (CC BY 4.0), Copernicus Atmosphere Monitoring Service. "
              "Havo sifati — model prognozi, o'lchov emas.",
              style: TextStyle(color: t.inkMuted, fontSize: 11),
            ),
          ),
        ],
      ),
    );
  }
}

class _ErrorBanner extends StatelessWidget {
  const _ErrorBanner(this.message);

  final String message;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: InfoCard(
        borderColor: t.danger,
        child: Row(
          children: [
            Icon(Icons.wifi_off, color: t.danger),
            const SizedBox(width: 12),
            Expanded(child: Text(message, style: TextStyle(color: t.ink))),
          ],
        ),
      ),
    );
  }
}

class _FirstLoad extends StatelessWidget {
  const _FirstLoad({required this.refreshing, required this.onRetry});

  final bool refreshing;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(top: 80),
        child: refreshing
            ? const EmptyState(
                icon: Icons.thermostat,
                title: 'Prognoz yuklanmoqda…',
                message: 'Ob-havo va havo sifati prognozi tahlil qilinmoqda.',
              )
            : EmptyState(
                icon: Icons.cloud_download_outlined,
                title: "Ma'lumot hali yuklanmagan",
                message: 'Internetga ulaning va yangilang.',
                action: FilledButton(onPressed: onRetry, child: const Text('Yangilash')),
              ),
      );
}
