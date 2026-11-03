import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../data/models.dart';
import '../theme.dart';
import '../util/format.dart';

/// Soatlik harorat grafigi (tashqi kutubxonasiz): havo harorati va issiqlik ko'rsatkichi.
class TempChart extends StatelessWidget {
  const TempChart({super.key, required this.hours, this.height = 150});

  final List<HourPoint> hours;
  final double height;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final pts = hours.where((h) => h.temp != null).toList();
    if (pts.length < 2) return _NoData(height: height);
    final peak = pts.reduce((a, b) => (b.feels ?? b.temp!) > (a.feels ?? a.temp!) ? b : a);
    return Semantics(
      label: 'Soatlik harorat grafigi. Eng yuqori issiqlik ko\'rsatkichi ${deg(peak.feels)}, '
          'soat ${hourLabel(peak.time.hour)}.',
      excludeSemantics: true,
      child: SizedBox(
        height: height,
        width: double.infinity,
        child: CustomPaint(
          painter: _TempPainter(
            hours: pts,
            temp: t.inkMuted,
            feels: t.accent,
            grid: t.line,
            label: t.inkMuted,
            danger: context.levelColor('WARNING'),
          ),
        ),
      ),
    );
  }
}

/// Soatlik PM2.5 ustunlari; JSST 24 soatlik tavsiyasi (15 µg/m³) chizig'i bilan.
class Pm25Chart extends StatelessWidget {
  const Pm25Chart({super.key, required this.hours, this.height = 120});

  final List<HourPoint> hours;
  final double height;

  static const who = 15.0;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final pts = hours.where((h) => h.pm25 != null).toList();
    if (pts.length < 2) return _NoData(height: height);
    final maxV = pts.map((h) => h.pm25!).reduce(math.max);
    return Semantics(
      label: 'Soatlik PM2.5 grafigi. Eng yuqori ${maxV.round()} mikrogramm kub metrda, JSST tavsiyasi 15.',
      excludeSemantics: true,
      child: SizedBox(
        height: height,
        width: double.infinity,
        child: CustomPaint(
          painter: _BarPainter(
            hours: pts,
            ok: context.levelColor('CALM'),
            high: context.levelColor('ADVISORY'),
            veryHigh: context.levelColor('EMERGENCY'),
            grid: t.line,
            label: t.inkMuted,
          ),
        ),
      ),
    );
  }
}

class _NoData extends StatelessWidget {
  const _NoData({required this.height});

  final double height;

  @override
  Widget build(BuildContext context) => SizedBox(
        height: math.min(height, 60),
        child: Center(child: Text("Grafik uchun ma'lumot yetarli emas", style: TextStyle(color: context.tokens.inkMuted))),
      );
}

const _left = 30.0;
const _bottom = 18.0;

void _text(Canvas canvas, String s, Offset at, Color color) {
  final tp = TextPainter(
    text: TextSpan(text: s, style: TextStyle(color: color, fontSize: 10, fontFamily: 'NotoSans')),
    textDirection: TextDirection.ltr,
  )..layout();
  tp.paint(canvas, at);
}

/// Har 6 soatda vaqt belgisi; `x` — grafikdagi i-soat nuqtasi (chiziq yoki ustun markazi).
void _timeAxis(Canvas canvas, Size size, List<HourPoint> hours, Color color, double Function(int i) x) {
  final h = size.height - _bottom;
  for (var i = 0; i < hours.length; i++) {
    if (hours[i].time.hour % 6 != 0) continue;
    final px = x(i);
    if (px > size.width - 26) continue;
    _text(canvas, hourLabel(hours[i].time.hour), Offset(math.max(px - 12, _left - 4), h + 3), color);
  }
}

/// Gorizontal shtrix chiziq (chegara belgisi).
void _dashed(Canvas canvas, double y, double from, double to, Color color) {
  final paint = Paint()
    ..color = color
    ..strokeWidth = 1.2;
  for (var dx = from; dx < to; dx += 8) {
    canvas.drawLine(Offset(dx, y), Offset(math.min(dx + 4, to), y), paint);
  }
}

class _TempPainter extends CustomPainter {
  _TempPainter({
    required this.hours,
    required this.temp,
    required this.feels,
    required this.grid,
    required this.label,
    required this.danger,
  });

  final List<HourPoint> hours;
  final Color temp;
  final Color feels;
  final Color grid;
  final Color label;
  final Color danger;

  /// NWS «Xavf» toifasi chegarasi.
  static const dangerLine = 39.4;

  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width - _left;
    final h = size.height - _bottom;
    final values = [for (final p in hours) ...[p.temp!, p.feels ?? p.temp!]];
    final lo = (values.reduce(math.min) / 5).floor() * 5.0;
    final hi = math.max(lo + 10, (values.reduce(math.max) / 5).ceil() * 5.0);
    double y(double v) => h - (v - lo) / (hi - lo) * h;
    double x(int i) => _left + i / (hours.length - 1) * w;

    final gridPaint = Paint()
      ..color = grid
      ..strokeWidth = 1;
    for (var i = 0; i <= 2; i++) {
      final v = lo + (hi - lo) * i / 2;
      canvas.drawLine(Offset(_left, y(v)), Offset(size.width, y(v)), gridPaint);
      _text(canvas, '${v.round()}°', Offset(0, y(v) - 7), label);
    }
    if (dangerLine > lo && dangerLine < hi) _dashed(canvas, y(dangerLine), _left, size.width, danger);
    _timeAxis(canvas, size, hours, label, x);

    Path line(double Function(HourPoint) f) {
      final p = Path();
      for (var i = 0; i < hours.length; i++) {
        i == 0 ? p.moveTo(x(i), y(f(hours[i]))) : p.lineTo(x(i), y(f(hours[i])));
      }
      return p;
    }

    canvas.drawPath(
      line((p) => p.temp!),
      Paint()
        ..color = temp
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.6,
    );
    canvas.drawPath(
      line((p) => p.feels ?? p.temp!),
      Paint()
        ..color = feels
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.4
        ..strokeJoin = StrokeJoin.round,
    );
  }

  @override
  bool shouldRepaint(_TempPainter old) => old.hours != hours || old.feels != feels;
}

class _BarPainter extends CustomPainter {
  _BarPainter({
    required this.hours,
    required this.ok,
    required this.high,
    required this.veryHigh,
    required this.grid,
    required this.label,
  });

  final List<HourPoint> hours;
  final Color ok;
  final Color high;
  final Color veryHigh;
  final Color grid;
  final Color label;

  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width - _left;
    final h = size.height - _bottom;
    final maxV = math.max(30.0, hours.map((p) => p.pm25!).reduce(math.max) * 1.1);
    double y(double v) => h - v / maxV * h;
    final gridPaint = Paint()
      ..color = grid
      ..strokeWidth = 1;
    canvas.drawLine(Offset(_left, h), Offset(size.width, h), gridPaint);
    _text(canvas, '${maxV.round()}', const Offset(0, -2), label);
    final barW = math.max(1.5, w / hours.length - 1.5);
    for (var i = 0; i < hours.length; i++) {
      final v = hours[i].pm25!;
      final color = v <= Pm25Chart.who ? ok : (v <= 37.5 ? high : veryHigh);
      final x = _left + i / hours.length * w;
      canvas.drawRect(Rect.fromLTRB(x, y(v), x + barW, h), Paint()..color = color.withValues(alpha: 0.85));
    }
    // JSST tavsiyasi chizig'i.
    final wy = y(Pm25Chart.who);
    _dashed(canvas, wy, _left, size.width, label);
    _text(canvas, 'JSST 15', Offset(0, wy - 7), label);
    _timeAxis(canvas, size, hours, label, (i) => _left + (i + 0.5) / hours.length * w);
  }

  @override
  bool shouldRepaint(_BarPainter old) => old.hours != hours || old.ok != ok;
}
