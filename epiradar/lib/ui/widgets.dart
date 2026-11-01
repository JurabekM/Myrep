import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../data/models.dart';
import '../theme.dart';
import '../util/format.dart';

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

/// Hodisa kartasi (ro'yxatlar uchun).
class EventTile extends StatelessWidget {
  const EventTile({super.key, required this.event, required this.onTap});

  final OutbreakEvent event;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final color = context.levelColor(event.personal.level);
    return InfoCard(
      onTap: onTap,
      padding: EdgeInsets.zero,
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
                        LevelBadge(event.personal),
                        const Spacer(),
                        Text(timeAgo(event.lastUpdated), style: TextStyle(color: t.inkMuted, fontSize: 12)),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(event.title, style: TextStyle(fontWeight: FontWeight.w700, color: t.ink, fontSize: 15)),
                    if (event.flags.isNotEmpty) ...[
                      const SizedBox(height: 4),
                      Text(event.flags.take(2).join(' · '), style: TextStyle(color: t.accentText, fontSize: 13)),
                    ],
                    const SizedBox(height: 6),
                    Text(
                      [
                        '${event.signals.length} ta xabar',
                        '${event.sources.length} ta manba',
                        if (event.distanceKm != null) event.distanceKm == 0 ? 'mamlakatingizda' : '~${formatInt((event.distanceKm! / 100).round() * 100)} km',
                      ].join(' · '),
                      style: TextStyle(color: t.inkMuted, fontSize: 12),
                    ),
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

/// Oddiy chiziqli grafik (tashqi kutubxonasiz): qiymatlar, anomaliya nuqtalari va o'q belgilari.
class TrendChart extends StatelessWidget {
  const TrendChart({super.key, required this.trend, this.height = 160});

  final Trend trend;
  final double height;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    if (trend.points.length < 2) {
      return SizedBox(
        height: 60,
        child: Center(child: Text("Grafik uchun ma'lumot yetarli emas", style: TextStyle(color: t.inkMuted))),
      );
    }
    final last = trend.points.last;
    return Semantics(
      label: '${trend.title}. Oxirgi qiymat ${formatPercent(last.value)}, ${formatShortDate(last.week)} haftasi. ${trend.statusName}.',
      excludeSemantics: true,
      child: SizedBox(
        height: height,
        width: double.infinity,
        child: CustomPaint(
          painter: _ChartPainter(
            points: trend.points,
            anomalies: trend.anomalies,
            line: t.accent,
            grid: t.line,
            label: t.inkMuted,
            anomaly: context.levelColor('EMERGENCY'),
          ),
        ),
      ),
    );
  }
}

class _ChartPainter extends CustomPainter {
  _ChartPainter({
    required this.points,
    required this.anomalies,
    required this.line,
    required this.grid,
    required this.label,
    required this.anomaly,
  });

  final List<TrendPoint> points;
  final List<Anomaly> anomalies;
  final Color line;
  final Color grid;
  final Color label;
  final Color anomaly;

  @override
  void paint(Canvas canvas, Size size) {
    const left = 34.0;
    const bottom = 18.0;
    final w = size.width - left;
    final h = size.height - bottom;
    final t0 = points.first.week.millisecondsSinceEpoch.toDouble();
    final t1 = points.last.week.millisecondsSinceEpoch.toDouble();
    final maxV = math.max(10.0, points.map((p) => p.value).reduce(math.max) * 1.15);

    Offset pos(DateTime d, double v) =>
        Offset(left + (t1 == t0 ? 0 : (d.millisecondsSinceEpoch - t0) / (t1 - t0)) * w, h - (v / maxV) * h);

    final gridPaint = Paint()
      ..color = grid
      ..strokeWidth = 1;
    for (var i = 0; i <= 3; i++) {
      final v = maxV * i / 3;
      final y = h - (v / maxV) * h;
      canvas.drawLine(Offset(left, y), Offset(size.width, y), gridPaint);
      _text(canvas, '${v.round()}%', Offset(0, y - 7));
    }
    _text(canvas, formatShortDate(points.first.week), Offset(left, h + 3));
    final endLabel = formatShortDate(points.last.week);
    _text(canvas, endLabel, Offset(size.width - endLabel.length * 6.2, h + 3));

    final path = Path();
    final area = Path();
    for (var i = 0; i < points.length; i++) {
      final p = pos(points[i].week, points[i].value);
      if (i == 0) {
        path.moveTo(p.dx, p.dy);
        area.moveTo(p.dx, h);
        area.lineTo(p.dx, p.dy);
      } else {
        path.lineTo(p.dx, p.dy);
        area.lineTo(p.dx, p.dy);
      }
    }
    area.lineTo(pos(points.last.week, 0).dx, h);
    area.close();
    canvas.drawPath(area, Paint()..color = line.withValues(alpha: 0.12));
    canvas.drawPath(
      path,
      Paint()
        ..color = line
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.2
        ..strokeJoin = StrokeJoin.round,
    );
    for (final a in anomalies) {
      if (a.week.isBefore(points.first.week)) continue;
      final p = pos(a.week, a.value);
      canvas.drawCircle(p, 5.5, Paint()..color = anomaly);
      canvas.drawCircle(
        p,
        5.5,
        Paint()
          ..color = Colors.black.withValues(alpha: 0.4)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.5,
      );
    }
  }

  void _text(Canvas canvas, String s, Offset at) {
    final tp = TextPainter(
      text: TextSpan(text: s, style: TextStyle(color: label, fontSize: 10, fontFamily: 'NotoSans')),
      textDirection: TextDirection.ltr,
    )..layout();
    tp.paint(canvas, at);
  }

  @override
  bool shouldRepaint(_ChartPainter old) => old.points != points || old.anomalies != anomalies || old.line != line;
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
        "EpiRadar ma'lumot beradi, tashxis qo'ymaydi va shifokor o'rnini bosmaydi. "
        "Rasmiy ko'rsatmalar uchun sog'liqni saqlash organlariga murojaat qiling.",
        style: TextStyle(color: t.inkMuted, fontSize: 12, height: 1.4),
      ),
    );
  }
}
