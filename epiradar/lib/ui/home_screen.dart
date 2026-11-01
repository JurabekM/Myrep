import 'package:flutter/material.dart';

import '../data/models.dart';
import '../state/app_state.dart';
import '../theme.dart';
import '../util/format.dart';
import 'event_detail_screen.dart';
import 'settings_screen.dart';
import 'widgets.dart';

/// Bosh ekran — «radar»: mamlakatingiz uchun xavf darajasi va eng muhim signallar.
class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key, required this.onShowEvents, required this.onShowTrends});

  final VoidCallback onShowEvents;
  final VoidCallback onShowTrends;

  @override
  Widget build(BuildContext context) {
    final state = AppScope.of(context);
    final snap = state.snapshot;
    final t = context.tokens;
    return Scaffold(
      appBar: AppBar(
        title: const Text('EpiRadar'),
        actions: [
          if (state.refreshing)
            const Padding(
              padding: EdgeInsets.all(14),
              child: SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2.4)),
            )
          else
            IconButton(tooltip: 'Yangilash', icon: const Icon(Icons.refresh), onPressed: state.refresh),
          const SettingsButton(),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: state.refresh,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 4, 16, 32),
          children: [
            if (state.error != null) _ErrorBanner(state.error!),
            if (snap == null)
              _FirstLoad(refreshing: state.refreshing, onRetry: state.refresh)
            else ...[
              _HeroCard(snapshot: snap),
              const SectionTitle('Siz uchun eng muhim'),
              ..._topEvents(context, snap),
              if (snap.events.length > 3)
                Align(
                  alignment: Alignment.centerRight,
                  child: TextButton(onPressed: onShowEvents, child: Text('Barcha ${snap.events.length} ta hodisa')),
                ),
              _TrendSummary(snapshot: snap, onTap: onShowTrends),
              const SectionTitle('Shoshilinch yordam'),
              _EmergencyCard(country: snap.country),
              SectionTitle('Manbalar holati', trailing: Text(timeAgo(snap.generatedAt), style: TextStyle(color: t.inkMuted, fontSize: 12))),
              _SourcesCard(sources: snap.sources),
              const MedicalDisclaimer(),
            ],
          ],
        ),
      ),
    );
  }

  List<Widget> _topEvents(BuildContext context, Snapshot snap) {
    if (snap.events.isEmpty) {
      return [
        const InfoCard(
          child: Text("So'nggi 6 oyda rasmiy manbalarda faol tahdid qayd etilmagan."),
        ),
      ];
    }
    return [
      for (final e in snap.events.take(3))
        Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: EventTile(event: e, onTap: () => openEvent(context, e)),
        ),
    ];
  }
}

void openEvent(BuildContext context, OutbreakEvent e) =>
    Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => EventDetailScreen(eventId: e.id)));

class _HeroCard extends StatelessWidget {
  const _HeroCard({required this.snapshot});

  final Snapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final p = snapshot.personal;
    return InfoCard(
      borderColor: context.levelColor(p.level).withValues(alpha: 0.6),
      padding: const EdgeInsets.fromLTRB(16, 20, 16, 16),
      child: Column(
        children: [
          Text('${snapshot.countryName} uchun xavf darajasi', style: TextStyle(color: t.inkMuted)),
          const SizedBox(height: 12),
          ScoreGauge(level: p),
          const SizedBox(height: 12),
          Text(p.advice, textAlign: TextAlign.center, style: TextStyle(color: t.ink, height: 1.4)),
          const SizedBox(height: 14),
          Wrap(
            alignment: WrapAlignment.center,
            spacing: 8,
            runSpacing: 8,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              LevelBadge(snapshot.global, prefix: 'Dunyo'),
              TextButton.icon(
                onPressed: () => showLevelsSheet(context),
                icon: const Icon(Icons.info_outline, size: 18),
                label: const Text('Darajalar nimani anglatadi?'),
              ),
            ],
          ),
        ],
      ),
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
              "Ball 0–100: qo'zg'atuvchi xavfi, epidemiologik belgilar (noma'lum sabab, odamdan odamga yuqish, "
              "tarqalish), rasmiy sayohat darajasi, manbalar soni, yangilik va sizgacha bo'lgan masofadan hisoblanadi.",
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
                      width: 96,
                      child: LevelBadge(Level(score: l.minScore, level: l.level, name: l.name, advice: l.advice), showScore: false),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text('${l.minScore}+ ball. ${l.advice}', style: TextStyle(color: t.ink, height: 1.35)),
                    ),
                  ],
                ),
              ),
          ],
        ),
      );
    },
  );
}

class _TrendSummary extends StatelessWidget {
  const _TrendSummary({required this.snapshot, required this.onTap});

  final Snapshot snapshot;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final alerts = snapshot.trends.where((x) => x.status == 'UNUSUAL' || x.status == 'RISING' || x.novelFluWeeks.isNotEmpty).toList();
    final home = snapshot.trends.where((x) => x.country == snapshot.country).firstOrNull;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SectionTitle('Gripp kuzatuvi (JSST FluNet)'),
        InfoCard(
          onTap: onTap,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (alerts.isEmpty)
                Row(
                  children: [
                    Icon(Icons.check_circle_outline, color: context.levelColor('CALM')),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        "Siz va qo'shni mamlakatlarda gripp faolligi me'yoridan oshgani aniqlanmadi.",
                        style: TextStyle(color: t.ink),
                      ),
                    ),
                  ],
                )
              else
                for (final a in alerts)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 6),
                    child: Row(
                      children: [
                        Icon(Icons.trending_up, color: context.levelColor(a.novelFluWeeks.isNotEmpty ? 'WARNING' : 'ADVISORY')),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            a.novelFluWeeks.isNotEmpty ? '${a.countryName}: odamda qush grippi aniqlangan' : '${a.countryName}: ${a.statusName.toLowerCase()}',
                            style: TextStyle(color: t.ink),
                          ),
                        ),
                      ],
                    ),
                  ),
              if (home != null) ...[
                const SizedBox(height: 8),
                Text(home.note, style: TextStyle(color: t.inkMuted, fontSize: 13)),
              ],
            ],
          ),
        ),
      ],
    );
  }
}

class _EmergencyCard extends StatelessWidget {
  const _EmergencyCard({required this.country});

  final String country;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final state = AppScope.read(context);
    final uz = country == 'UZB';
    final number = uz ? '103' : '112';
    return InfoCard(
      child: Row(
        children: [
          Icon(Icons.local_hospital_outlined, color: t.danger, size: 32),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(uz ? 'Tez tibbiy yordam — 103' : "Favqulodda raqam — 112 (ko'p mamlakatlarda)",
                    style: TextStyle(fontWeight: FontWeight.w700, color: t.ink)),
                const SizedBox(height: 2),
                Text(
                  "Xavfli hududdan qaytgach isitma bo'lsa — qo'ng'iroqda safaringiz haqida oldindan ayting.",
                  style: TextStyle(color: t.inkMuted, fontSize: 13),
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          FilledButton(
            onPressed: () => state.engine.dial(number),
            style: FilledButton.styleFrom(minimumSize: const Size(56, 56), padding: const EdgeInsets.symmetric(horizontal: 16)),
            child: const Icon(Icons.call),
          ),
        ],
      ),
    );
  }
}

class _SourcesCard extends StatelessWidget {
  const _SourcesCard({required this.sources});

  final List<SourceStatus> sources;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final state = AppScope.read(context);
    return InfoCard(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Column(
        children: [
          for (final s in sources)
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
                    ? '${s.itemCount} ta yozuv'
                    : '${s.error ?? 'Xato'}${s.stale ? " — oxirgi saqlangan ma'lumot (${s.fetchedAt == null ? '' : timeAgo(s.fetchedAt!)})" : ''}',
                style: TextStyle(color: t.inkMuted),
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
                icon: Icons.radar,
                title: "Rasmiy manbalardan ma'lumot yig'ilmoqda…",
                message: 'JSST, ECDC, CDC va JSST FluNet tahlil qilinmoqda.',
              )
            : EmptyState(
                icon: Icons.cloud_download_outlined,
                title: "Ma'lumot hali yuklanmagan",
                message: 'Internetga ulaning va yangilang.',
                action: FilledButton(onPressed: onRetry, child: const Text('Yangilash')),
              ),
      );
}
