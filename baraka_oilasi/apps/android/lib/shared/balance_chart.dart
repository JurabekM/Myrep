import 'package:flutter/material.dart';

import '../app/i18n.dart';
import '../app/theme.dart';
import '../core/core.dart';
import 'format.dart';

/// Umumiy qoldiq: odatiy va qo'shimcha to'lovli prognoz (bitta o'q, ikki chiziq).
/// Qiymatlar faqat chizish uchun songa aylantiriladi; matnlar yadrodagi `formatted` dan.
class BalanceChart extends StatefulWidget {
  const BalanceChart({required this.points, super.key});

  final List<TimelinePointDto> points;

  @override
  State<BalanceChart> createState() => _BalanceChartState();
}

class _BalanceChartState extends State<BalanceChart> {
  int? _hover;

  @override
  Widget build(BuildContext context) {
    final pts = widget.points;
    if (pts.isEmpty) return const SizedBox.shrink();
    final p = context.palette;
    final h = _hover == null ? null : pts[_hover!];
    Widget legend(Color c, String text) => Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(width: 18, height: 3, color: c),
        const SizedBox(width: 6),
        Text(text, style: TextStyle(color: p.inkMuted, fontSize: 13)),
      ],
    );
    return Semantics(
      label: context.t('payoff.chart.aria'),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(context.t('payoff.chart.title'), style: TextStyle(color: p.inkMuted, fontSize: 13)),
          const SizedBox(height: 4),
          Wrap(
            spacing: 16,
            children: [
              legend(p.chart1, context.t('payoff.chart.base')),
              legend(p.chart2, context.t('payoff.chart.accelerated')),
            ],
          ),
          const SizedBox(height: 8),
          LayoutBuilder(
            builder: (context, box) {
              void pick(Offset local) {
                final i = pts.length == 1 ? 0 : (local.dx / box.maxWidth * (pts.length - 1)).round();
                setState(() => _hover = i.clamp(0, pts.length - 1));
              }

              return GestureDetector(
                onTapDown: (d) => pick(d.localPosition),
                onHorizontalDragUpdate: (d) => pick(d.localPosition),
                child: CustomPaint(
                  size: Size(box.maxWidth, 180),
                  painter: _ChartPainter(pts, _hover, p),
                ),
              );
            },
          ),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(showMonth(pts.first.month), style: TextStyle(color: p.inkMuted, fontSize: 12)),
              Text(showMonth(pts.last.month), style: TextStyle(color: p.inkMuted, fontSize: 12)),
            ],
          ),
          if (h != null)
            Semantics(
              liveRegion: true,
              child: Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  '${showMonth(h.month)} · ${context.t('payoff.chart.base')}: ${h.baseBalance.formatted} · '
                  '${context.t('payoff.chart.accelerated')}: ${h.acceleratedBalance.formatted}',
                  style: const TextStyle(fontSize: 13),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _ChartPainter extends CustomPainter {
  _ChartPainter(this.points, this.hover, this.p);

  final List<TimelinePointDto> points;
  final int? hover;
  final BarakaPalette p;

  @override
  void paint(Canvas canvas, Size size) {
    // Faqat chizish uchun: minor birliklar → double (pul hisobi emas).
    final base = [for (final x in points) double.tryParse(x.baseBalance.minor) ?? 0];
    final fast = [for (final x in points) double.tryParse(x.acceleratedBalance.minor) ?? 0];
    final max = [...base, ...fast, 1.0].reduce((a, b) => a > b ? a : b);
    double x(int i) => points.length == 1 ? 0 : i / (points.length - 1) * size.width;
    double y(double v) => size.height - v / max * size.height;
    final grid = Paint()
      ..color = p.line
      ..strokeWidth = 1;
    for (final f in [0.0, 0.5, 1.0]) {
      canvas.drawLine(Offset(0, size.height * f), Offset(size.width, size.height * f), grid);
    }
    Path path(List<double> vs, int last) {
      final pth = Path()..moveTo(x(0), y(vs[0]));
      for (var i = 1; i <= last; i++) {
        pth.lineTo(x(i), y(vs[i]));
      }
      return pth;
    }

    Paint line(Color c) => Paint()
      ..color = c
      ..strokeWidth = 2.5
      ..style = PaintingStyle.stroke
      ..strokeJoin = StrokeJoin.round
      ..strokeCap = StrokeCap.round;
    canvas.drawPath(path(base, base.length - 1), line(p.chart1));
    final end = fast.indexWhere((v) => v == 0);
    final fastLast = end == -1 ? fast.length - 1 : end;
    canvas
      ..drawPath(path(fast, fastLast), line(p.chart2))
      ..drawCircle(Offset(x(fastLast), y(0)), 5, Paint()..color = p.chart2);
    final h = hover;
    if (h != null) {
      canvas
        ..drawLine(Offset(x(h), 0), Offset(x(h), size.height), Paint()..color = p.inkMuted)
        ..drawCircle(Offset(x(h), y(base[h])), 5, Paint()..color = p.chart1)
        ..drawCircle(Offset(x(h), y(fast[h])), 5, Paint()..color = p.chart2);
    }
  }

  @override
  bool shouldRepaint(_ChartPainter old) => old.points != points || old.hover != hover || old.p != p;
}
