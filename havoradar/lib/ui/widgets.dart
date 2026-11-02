import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../data/models.dart';
import '../theme.dart';

/// Xavf darajasi yorlig'i (rang + matn; faqat rangga tayanmaymiz — rang ko'rlik uchun matn ham bor).
class LevelBadge extends StatelessWidget {
  const LevelBadge(this.level, {super.key, this.showScore = true, this.prefix});

  final Level level;
  final bool showScore;
  final String? prefix;

  @override
  Widget build(BuildContext context) {
    final c = context.levelColor(level.level);
    final text = [?prefix, level.name, if (showScore) '${level.score}'].join(' · ');
    return Semantics(
      label: 'Xavf darajasi: ${level.name}, ball ${level.score}',
      excludeSemantics: true,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
          color: c.withValues(alpha: 0.14),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: c.withValues(alpha: 0.6)),
        ),
        child: Text(text, style: TextStyle(color: c, fontWeight: FontWeight.w700, fontSize: 12)),
      ),
    );
  }
}

/// Yarim doira shkala: 5 daraja segmenti va strelka (Google zilzila ogohlantirishidagi kabi aniq).
class ScoreGauge extends StatelessWidget {
  const ScoreGauge({super.key, required this.level, this.size = 220});

  final Level level;
  final double size;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final colors = Level.order.map(context.levelColor).toList();
    return Semantics(
      label: 'Xavf balli ${level.score} dan 100, daraja ${level.name}',
      excludeSemantics: true,
      child: SizedBox(
        width: size,
        height: size * 0.62,
        child: TweenAnimationBuilder<double>(
          tween: Tween(begin: 0, end: level.score.toDouble()),
          duration: const Duration(milliseconds: 900),
          curve: Curves.easeOutCubic,
          builder: (context, value, _) => CustomPaint(
            painter: _GaugePainter(value: value, colors: colors, track: t.line, needle: t.ink),
            child: Align(
              alignment: const Alignment(0, 0.95),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    '${value.round()}',
                    style: TextStyle(fontSize: size * 0.2, fontWeight: FontWeight.w700, color: context.levelColor(level.level), height: 1),
                  ),
                  const SizedBox(height: 4),
                  Text(level.name, style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: t.ink)),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _GaugePainter extends CustomPainter {
  _GaugePainter({required this.value, required this.colors, required this.track, required this.needle});

  final double value;
  final List<Color> colors;
  final Color track;
  final Color needle;

  static const _bounds = [0, 20, 40, 60, 80, 100];

  @override
  void paint(Canvas canvas, Size size) {
    final stroke = size.width * 0.075;
    final radius = size.width / 2 - stroke / 2;
    final center = Offset(size.width / 2, size.width / 2);
    final rect = Rect.fromCircle(center: center, radius: radius);
    for (var i = 0; i < 5; i++) {
      final start = math.pi + math.pi * _bounds[i] / 100;
      final sweep = math.pi * (_bounds[i + 1] - _bounds[i]) / 100 - 0.03;
      final active = value >= _bounds[i];
      canvas.drawArc(
        rect,
        start,
        sweep,
        false,
        Paint()
          ..color = active ? colors[i] : colors[i].withValues(alpha: 0.25)
          ..style = PaintingStyle.stroke
          ..strokeWidth = stroke
          ..strokeCap = StrokeCap.butt,
      );
    }
    final angle = math.pi + math.pi * value.clamp(0, 100) / 100;
    final tip = center + Offset(math.cos(angle), math.sin(angle)) * (radius - stroke * 0.9);
    canvas.drawLine(
      center + Offset(math.cos(angle), math.sin(angle)) * (radius * 0.55),
      tip,
      Paint()
        ..color = needle
        ..strokeWidth = 3
        ..strokeCap = StrokeCap.round,
    );
  }

  @override
  bool shouldRepaint(_GaugePainter old) => old.value != value || old.colors != colors;
}

class SectionTitle extends StatelessWidget {
  const SectionTitle(this.text, {super.key, this.trailing});

  final String text;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(4, 20, 4, 8),
        child: Row(
          children: [
            Expanded(
              child: Semantics(
                header: true,
                child: Text(text, style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: context.tokens.ink)),
              ),
            ),
            ?trailing,
          ],
        ),
      );
}

class InfoCard extends StatelessWidget {
  const InfoCard({super.key, required this.child, this.onTap, this.padding = const EdgeInsets.all(16), this.borderColor});

  final Widget child;
  final VoidCallback? onTap;
  final EdgeInsets padding;
  final Color? borderColor;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    return Material(
      color: t.surface,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16), side: BorderSide(color: borderColor ?? t.line)),
      clipBehavior: Clip.antiAlias,
      child: InkWell(onTap: onTap, child: Padding(padding: padding, child: child)),
    );
  }
}

class EmptyState extends StatelessWidget {
  const EmptyState({super.key, required this.icon, required this.title, this.message, this.action});

  final IconData icon;
  final String title;
  final String? message;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 48, color: t.inkMuted),
            const SizedBox(height: 12),
            Text(title, textAlign: TextAlign.center, style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: t.ink)),
            if (message != null) ...[
              const SizedBox(height: 6),
              Text(message!, textAlign: TextAlign.center, style: TextStyle(color: t.inkMuted)),
            ],
            if (action != null) ...[const SizedBox(height: 16), action!],
          ],
        ),
      ),
    );
  }
}

/// Matnli bo'lim (sarlavha + nuqtali ro'yxat).
class BulletList extends StatelessWidget {
  const BulletList(this.items, {super.key, this.color});

  final List<String> items;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (final i in items)
          Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Padding(
                  padding: const EdgeInsets.only(top: 7, right: 10),
                  child: Container(width: 6, height: 6, decoration: BoxDecoration(color: color ?? t.accent, shape: BoxShape.circle)),
                ),
                Expanded(child: Text(i, style: TextStyle(color: t.ink, height: 1.4))),
              ],
            ),
          ),
      ],
    );
  }
}

/// Tibbiy ogohlantirish (har bir tibbiy ekranda).
class MedicalDisclaimer extends StatelessWidget {
  const MedicalDisclaimer({super.key});

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 16),
      child: Text(
        "HavoRadar ma'lumot beradi, tashxis qo'ymaydi va shifokor o'rnini bosmaydi. "
        "Ob-havo va havo sifati — model prognozi; rasmiy ogohlantirishlarga ham amal qiling.",
        style: TextStyle(color: t.inkMuted, fontSize: 12, height: 1.4),
      ),
    );
  }
}
