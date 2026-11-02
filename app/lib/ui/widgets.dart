
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../core/native.dart';
import '../core/risk.dart';
import 'theme.dart';

class VerdictBanner extends StatelessWidget {
  const VerdictBanner({super.key, required this.severity, required this.title, required this.subtitle});
  final Severity severity;
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    final c = RColors.of(severity);
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: c.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: c.withValues(alpha: 0.7), width: 1.5),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(RColors.icon(severity), color: c, size: 36),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: TextStyle(color: c, fontSize: 18, fontWeight: FontWeight.w800)),
                const SizedBox(height: 4),
                Text(subtitle, style: const TextStyle(color: RColors.text, fontSize: 14, height: 1.4)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class SeverityChip extends StatelessWidget {
  const SeverityChip(this.severity, {super.key});
  final Severity severity;

  @override
  Widget build(BuildContext context) {
    final c = RColors.of(severity);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(color: c.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(8)),
      child: Text(severity.label, style: TextStyle(color: c, fontSize: 12, fontWeight: FontWeight.w700)),
    );
  }
}

class FindingCard extends StatelessWidget {
  const FindingCard(this.finding, {super.key, this.dimmed = false});
  final Finding finding;
  final bool dimmed;

  @override
  Widget build(BuildContext context) {
    final c = RColors.of(finding.severity);
    return Opacity(
      opacity: dimmed ? 0.55 : 1,
      child: Card(
        child: Theme(
          data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
          child: ExpansionTile(
            key: PageStorageKey(finding.code),
            initiallyExpanded: finding.severity >= Severity.high,
            tilePadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 2),
            childrenPadding: const EdgeInsets.fromLTRB(14, 0, 14, 14),
            leading: Icon(RColors.icon(finding.severity), color: c),
            title: Text(finding.title, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15)),
            subtitle: Padding(padding: const EdgeInsets.only(top: 4), child: Align(alignment: Alignment.centerLeft, child: SeverityChip(finding.severity))),
            iconColor: RColors.textDim,
            collapsedIconColor: RColors.textDim,
            expandedCrossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(finding.explain),
              if (finding.evidence != null) ...[
                const SizedBox(height: 10),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(color: RColors.bg, borderRadius: BorderRadius.circular(10)),
                  child: SelectableText(finding.evidence!, style: const TextStyle(fontFamily: 'monospace', fontSize: 12, color: RColors.textDim)),
                ),
              ],
              if (finding.action != null) ...[
                const SizedBox(height: 12),
                OutlinedButton.icon(
                  onPressed: () => Native.open(finding.action!.kind, finding.action!.arg),
                  icon: const Icon(Icons.settings_rounded, size: 18),
                  label: Text(finding.action!.label),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class SectionTitle extends StatelessWidget {
  const SectionTitle(this.text, {super.key});
  final String text;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(4, 20, 4, 8),
        child: Text(text.toUpperCase(), style: const TextStyle(color: RColors.textDim, fontSize: 12, letterSpacing: 1.1, fontWeight: FontWeight.w700)),
      );
}

class KV extends StatelessWidget {
  const KV(this.k, this.v, {super.key, this.mono = false});
  final String k;
  final String v;
  final bool mono;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(width: 120, child: Text(k, style: const TextStyle(color: RColors.textDim, fontSize: 13))),
            Expanded(child: SelectableText(v, style: TextStyle(fontSize: 13, fontFamily: mono ? 'monospace' : null))),
          ],
        ),
      );
}

/// Sertifikat izini 4 belgilik guruhlarda ko'rsatadi va nusxalashga imkon beradi.
class Fingerprint extends StatelessWidget {
  const Fingerprint(this.hex, {super.key});
  final String hex;
  @override
  Widget build(BuildContext context) {
    final up = hex.toUpperCase();
    final groups = [for (var i = 0; i < up.length; i += 4) up.substring(i, i + 4 > up.length ? up.length : i + 4)];
    return InkWell(
      borderRadius: BorderRadius.circular(10),
      onTap: () {
        Clipboard.setData(ClipboardData(text: hex));
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Nusxa olindi')));
      },
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(color: RColors.bg, borderRadius: BorderRadius.circular(10), border: Border.all(color: RColors.line)),
        child: Wrap(
          spacing: 10,
          runSpacing: 6,
          children: [for (final g in groups) Text(g, style: const TextStyle(fontFamily: 'monospace', fontSize: 14, color: RColors.accent, letterSpacing: 1))],
        ),
      ),
    );
  }
}

class AppIcon extends StatelessWidget {
  const AppIcon({super.key, this.bytes, this.package, this.size = 44});
  final Uint8List? bytes;
  final String? package;
  final double size;

  static final Map<String, Future<Uint8List?>> _cache = {};

  @override
  Widget build(BuildContext context) {
    Widget fallback() => Container(
          width: size, height: size,
          decoration: BoxDecoration(color: RColors.surfaceHi, borderRadius: BorderRadius.circular(12)),
          child: Icon(Icons.android_rounded, color: RColors.textDim, size: size * 0.6),
        );
    if (bytes != null) return ClipRRect(borderRadius: BorderRadius.circular(12), child: Image.memory(bytes!, width: size, height: size));
    if (package == null) return fallback();
    return FutureBuilder<Uint8List?>(
      future: _cache.putIfAbsent(package!, () => Native.appIcon(package!)),
      builder: (_, s) => s.data == null ? fallback() : ClipRRect(borderRadius: BorderRadius.circular(12), child: Image.memory(s.data!, width: size, height: size)),
    );
  }
}

String verdictTitle(Severity s) => switch (s) {
      Severity.critical => 'Xavfli',
      Severity.high => 'Jiddiy shubha',
      Severity.medium => 'Ehtiyot bo\'ling',
      Severity.low || Severity.info => 'Jiddiy belgi yo\'q',
      Severity.ok => 'Ishonchli',
    };
