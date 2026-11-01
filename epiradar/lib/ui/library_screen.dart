import 'package:flutter/material.dart';

import '../data/models.dart';
import '../state/app_state.dart';
import '../theme.dart';
import 'home_screen.dart';
import 'settings_screen.dart';
import 'widgets.dart';

/// Kasalliklar ma'lumotnomasi (oflayn): yuqish yo'li, alomatlar, oldini olish, qachon shifokorga.
class LibraryScreen extends StatefulWidget {
  const LibraryScreen({super.key});

  @override
  State<LibraryScreen> createState() => _LibraryScreenState();
}

class _LibraryScreenState extends State<LibraryScreen> {
  String query = '';

  @override
  Widget build(BuildContext context) {
    final state = AppScope.of(context);
    final t = context.tokens;
    final q = query.trim().toLowerCase();
    final active = {for (final e in state.snapshot?.events ?? const <OutbreakEvent>[]) e.diseaseId};
    final list = state.catalog.diseases
        .where((d) => d.id != 'other')
        .where((d) => q.isEmpty || d.name.toLowerCase().contains(q) || d.group.toLowerCase().contains(q) || d.symptoms.any((s) => s.toLowerCase().contains(q)))
        .toList()
      ..sort((a, b) {
        final act = (active.contains(b.id) ? 1 : 0).compareTo(active.contains(a.id) ? 1 : 0);
        return act != 0 ? act : b.hazard.compareTo(a.hazard);
      });
    return Scaffold(
      appBar: AppBar(title: const Text('Kasalliklar'), actions: const [SettingsButton()]),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 32),
        children: [
          TextField(
            decoration: const InputDecoration(prefixIcon: Icon(Icons.search), hintText: 'Kasallik, guruh yoki alomat'),
            onChanged: (v) => setState(() => query = v),
          ),
          const SizedBox(height: 12),
          for (final d in list) ...[
            InfoCard(
              onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => DiseaseDetailScreen(disease: d))),
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(d.name, style: TextStyle(fontWeight: FontWeight.w700, color: t.ink)),
                        const SizedBox(height: 4),
                        Text('${d.group} · pandemik salohiyat: ${d.pandemicName.toLowerCase()}', style: TextStyle(color: t.inkMuted, fontSize: 13)),
                      ],
                    ),
                  ),
                  if (active.contains(d.id))
                    Padding(
                      padding: const EdgeInsets.only(left: 8),
                      child: Text('faol', style: TextStyle(color: t.accentText, fontWeight: FontWeight.w700, fontSize: 12)),
                    ),
                  Icon(Icons.chevron_right, color: t.inkMuted),
                ],
              ),
            ),
            const SizedBox(height: 10),
          ],
          if (list.isEmpty) const EmptyState(icon: Icons.search_off, title: 'Hech narsa topilmadi'),
          const MedicalDisclaimer(),
        ],
      ),
    );
  }
}

class DiseaseDetailScreen extends StatelessWidget {
  const DiseaseDetailScreen({super.key, required this.disease});

  final Disease disease;

  @override
  Widget build(BuildContext context) {
    final state = AppScope.of(context);
    final t = context.tokens;
    final d = disease;
    final events = (state.snapshot?.events ?? const <OutbreakEvent>[]).where((e) => e.diseaseId == d.id).toList();
    Widget text(String s) => Text(s, style: TextStyle(color: t.ink, height: 1.45));
    return Scaffold(
      appBar: AppBar(title: Text(d.name, overflow: TextOverflow.ellipsis)),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 32),
        children: [
          Text(d.name, style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700, color: t.ink)),
          const SizedBox(height: 6),
          Text('${d.group} · pandemik salohiyat: ${d.pandemicName.toLowerCase()}', style: TextStyle(color: t.inkMuted)),
          if (events.isNotEmpty) ...[
            const SectionTitle('Hozir faol hodisalar'),
            for (final e in events) ...[
              EventTile(event: e, onTap: () => openEvent(context, e)),
              const SizedBox(height: 10),
            ],
          ],
          const SectionTitle("Yuqish yo'li"),
          InfoCard(child: text(d.transmission)),
          const SectionTitle('Yashirin davr va xavf'),
          InfoCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                text('Yashirin (inkubatsion) davr: ${d.incubation}'),
                const SizedBox(height: 6),
                text("O'lim darajasi: ${d.fatality}"),
              ],
            ),
          ),
          if (d.symptoms.isNotEmpty) ...[
            const SectionTitle('Alomatlar'),
            InfoCard(child: BulletList(d.symptoms)),
          ],
          if (d.prevention.isNotEmpty) ...[
            const SectionTitle('Oldini olish'),
            InfoCard(child: BulletList(d.prevention)),
          ],
          if (d.redFlags.isNotEmpty) ...[
            const SectionTitle('Qachon darhol shifokorga'),
            InfoCard(borderColor: t.danger, child: BulletList(d.redFlags, color: t.danger)),
          ],
          const SectionTitle('Vaksina va davolash'),
          InfoCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [text('Vaksina: ${d.vaccine}'), const SizedBox(height: 6), text('Davolash: ${d.treatment}')],
            ),
          ),
          if (d.localNote.isNotEmpty) ...[
            const SectionTitle('Mintaqa uchun izoh'),
            InfoCard(child: text(d.localNote)),
          ],
          const MedicalDisclaimer(),
        ],
      ),
    );
  }
}
