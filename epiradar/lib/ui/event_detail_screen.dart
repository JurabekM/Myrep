import 'package:flutter/material.dart';

import '../data/models.dart';
import '../state/app_state.dart';
import '../theme.dart';
import '../util/format.dart';
import 'library_screen.dart';
import 'widgets.dart';

/// Hodisa tafsilotlari: nega shu daraja, nima qilish kerak va asl manba xabarlari.
class EventDetailScreen extends StatelessWidget {
  const EventDetailScreen({super.key, required this.eventId});

  final String eventId;

  static const _travel = {
    1: 'Odatiy ehtiyot choralari',
    2: 'Kuchaytirilgan ehtiyot choralari',
    3: "Zaruriy bo'lmagan safarlarni qoldiring",
    4: "Barcha safarlardan voz keching",
  };

  @override
  Widget build(BuildContext context) {
    final state = AppScope.of(context);
    final t = context.tokens;
    final e = state.snapshot?.eventById(eventId);
    if (e == null) {
      return Scaffold(
        appBar: AppBar(),
        body: const EmptyState(icon: Icons.history, title: 'Hodisa endi faol emas', message: "U so'nggi yangilanishda ro'yxatdan chiqqan."),
      );
    }
    final disease = state.catalog.disease(e.diseaseId);
    return Scaffold(
      appBar: AppBar(
        title: Text(e.diseaseName, overflow: TextOverflow.ellipsis),
        actions: [
          IconButton(
            tooltip: 'Ulashish',
            icon: const Icon(Icons.share_outlined),
            onPressed: () => state.engine.share(_shareText(e)),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 32),
        children: [
          Text(e.title, style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700, color: t.ink, height: 1.3)),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              LevelBadge(e.personal, prefix: 'Siz uchun'),
              LevelBadge(e.global, prefix: 'Dunyo'),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            'Birinchi xabar: ${formatDate(e.firstSeen)} · oxirgi yangilanish: ${formatDate(e.lastUpdated)}',
            style: TextStyle(color: t.inkMuted, fontSize: 13),
          ),
          if (e.travelLevel != null) ...[
            const SizedBox(height: 12),
            InfoCard(
              borderColor: e.travelLevel! >= 3 ? t.danger : t.warn,
              child: Row(
                children: [
                  Icon(Icons.flight_takeoff, color: e.travelLevel! >= 3 ? t.danger : t.warn),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      'CDC sayohat darajasi ${e.travelLevel}/4: ${_travel[e.travelLevel]}',
                      style: TextStyle(color: t.ink, fontWeight: FontWeight.w700),
                    ),
                  ),
                ],
              ),
            ),
          ],
          const SectionTitle('Nega bu daraja?'),
          InfoCard(child: BulletList(e.reasons)),
          if (e.countries.isNotEmpty) ...[
            const SectionTitle('Mamlakatlar'),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final c in e.countries)
                  Chip(
                    label: Text(c.name),
                    avatar: c.iso3 == state.settings.country ? Icon(Icons.home, size: 16, color: t.accentText) : null,
                  ),
              ],
            ),
          ],
          const SectionTitle('Nima qilish kerak'),
          InfoCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(e.personal.advice, style: TextStyle(color: t.ink, fontWeight: FontWeight.w700, height: 1.4)),
                if (disease != null && disease.prevention.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  BulletList(disease.prevention),
                ],
              ],
            ),
          ),
          if (disease != null && disease.redFlags.isNotEmpty) ...[
            const SectionTitle('Qachon darhol shifokorga'),
            InfoCard(borderColor: t.danger, child: BulletList(disease.redFlags, color: t.danger)),
          ],
          if (disease != null) ...[
            const SectionTitle('Kasallik haqida qisqacha'),
            InfoCard(
              onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => DiseaseDetailScreen(disease: disease))),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _Fact('Yuqish yo\'li', disease.transmission),
                  _Fact('Yashirin davr', disease.incubation),
                  _Fact("O'lim darajasi", disease.fatality),
                  _Fact('Vaksina', disease.vaccine),
                  const SizedBox(height: 4),
                  Text("Batafsil ma'lumotnoma", style: TextStyle(color: t.accentText, fontWeight: FontWeight.w700)),
                ],
              ),
            ),
          ],
          SectionTitle('Manba xabarlari (${e.signals.length})'),
          for (final s in e.signals) ...[
            _SignalCard(signal: s),
            const SizedBox(height: 10),
          ],
          const MedicalDisclaimer(),
        ],
      ),
    );
  }

  String _shareText(OutbreakEvent e) {
    final link = e.signals.isEmpty ? '' : '\n${e.signals.first.url}';
    return '${e.title}\nXavf (siz uchun): ${e.personal.name} ${e.personal.score}/100\n${e.personal.advice}$link\n— EpiRadar';
  }
}

class _Fact extends StatelessWidget {
  const _Fact(this.label, this.value);

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: TextStyle(color: t.inkMuted, fontSize: 12)),
          const SizedBox(height: 2),
          Text(value, style: TextStyle(color: t.ink, height: 1.35)),
        ],
      ),
    );
  }
}

class _SignalCard extends StatelessWidget {
  const _SignalCard({required this.signal});

  final SignalItem signal;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final engine = AppScope.read(context).engine;
    return InfoCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.verified_outlined, size: 16, color: t.accentText),
              const SizedBox(width: 6),
              Expanded(child: Text(signal.sourceTitle, style: TextStyle(color: t.accentText, fontSize: 12, fontWeight: FontWeight.w700))),
              Text(formatShortDate(signal.publishedAt), style: TextStyle(color: t.inkMuted, fontSize: 12)),
            ],
          ),
          const SizedBox(height: 8),
          Text(signal.title, style: TextStyle(color: t.ink, fontWeight: FontWeight.w700)),
          if (signal.summary.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(signal.summary, maxLines: 6, overflow: TextOverflow.ellipsis, style: TextStyle(color: t.ink, height: 1.4)),
          ],
          const SizedBox(height: 8),
          Wrap(
            spacing: 4,
            children: [
              TextButton.icon(
                onPressed: () => engine.openUrl(signal.url),
                icon: const Icon(Icons.open_in_new, size: 18),
                label: const Text('Manbani ochish'),
              ),
              if (!signal.isUzbek)
                TextButton.icon(
                  onPressed: () => engine.openUrl(translateUrl('${signal.title}. ${signal.summary}')),
                  icon: const Icon(Icons.translate, size: 18),
                  label: const Text("O'zbekchaga tarjima"),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

/// Rasmiy manbalar inglizcha — foydalanuvchi so'rasa, matn tarjima xizmatida ochiladi.
String translateUrl(String text) {
  final clipped = text.length > 1800 ? text.substring(0, 1800) : text;
  return Uri.https('translate.google.com', '/', {'sl': 'en', 'tl': 'uz', 'text': clipped, 'op': 'translate'}).toString();
}
