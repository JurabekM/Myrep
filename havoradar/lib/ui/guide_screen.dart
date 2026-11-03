import 'package:flutter/material.dart';

import '../data/models.dart';
import '../state/app_state.dart';
import '../theme.dart';
import 'home_screen.dart';
import 'widgets.dart';

IconData guideIcon(String name) => switch (name) {
      'emergency' => Icons.emergency_outlined,
      'thermostat' => Icons.thermostat,
      'healing' => Icons.healing_outlined,
      'home' => Icons.home_outlined,
      'groups' => Icons.groups_outlined,
      'air' => Icons.air,
      'sun' => Icons.wb_sunny_outlined,
      _ => Icons.info_outline,
    };

/// Oflayn ma'lumotnoma: issiqlik kasalliklari, birinchi yordam, havo ifloslanishi, UV, sezgir guruhlar.
class GuideScreen extends StatelessWidget {
  const GuideScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final state = AppScope.of(context);
    final t = context.tokens;
    return Scaffold(
      appBar: AppBar(title: const Text("Ma'lumotnoma")),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
        children: [
          for (final g in state.catalog.guide) ...[
            InfoCard(
              borderColor: g.urgent ? t.danger : null,
              onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => GuideDetailScreen(entry: g))),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(guideIcon(g.icon), color: g.urgent ? t.danger : t.accentText),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(g.title, style: TextStyle(fontWeight: FontWeight.w700, color: t.ink)),
                        const SizedBox(height: 4),
                        Text(g.summary, style: TextStyle(color: t.inkMuted, height: 1.35, fontSize: 13)),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 10),
          ],
          InfoCard(
            onTap: () => showLevelsSheet(context),
            child: Row(
              children: [
                Icon(Icons.speed, color: t.accentText),
                const SizedBox(width: 14),
                Expanded(child: Text('Xavf darajalari qanday hisoblanadi', style: TextStyle(fontWeight: FontWeight.w700, color: t.ink))),
              ],
            ),
          ),
          const MedicalDisclaimer(),
        ],
      ),
    );
  }
}

class GuideDetailScreen extends StatelessWidget {
  const GuideDetailScreen({super.key, required this.entry});

  final GuideEntry entry;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final state = AppScope.read(context);
    return Scaffold(
      appBar: AppBar(title: Text(entry.title)),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
        children: [
          Text(entry.summary, style: TextStyle(color: t.ink, height: 1.45, fontSize: 15)),
          if (entry.urgent) ...[
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: () => state.engine.dial('103'),
              icon: const Icon(Icons.call),
              label: const Text("103 — tez yordamga qo'ng'iroq"),
            ),
          ],
          for (final s in entry.sections) ...[
            SectionTitle(s.title),
            InfoCard(child: BulletList(s.items)),
          ],
          const SectionTitle('Manbalar'),
          for (final src in entry.sources)
            TextButton.icon(
              style: TextButton.styleFrom(alignment: Alignment.centerLeft),
              onPressed: () => state.engine.openUrl(src.url),
              icon: const Icon(Icons.open_in_new, size: 18),
              label: Text(src.name),
            ),
          const MedicalDisclaimer(),
        ],
      ),
    );
  }
}
