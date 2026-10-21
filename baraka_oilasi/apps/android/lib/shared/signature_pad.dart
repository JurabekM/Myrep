import 'package:flutter/material.dart';

import '../app/i18n.dart';
import 'widgets.dart';

/// Yadrodagi imzo maydoni (`baraka_agreements::PAD_WIDTH × PAD_HEIGHT`).
const padW = 1000;
const padH = 400;

/// Imzo chiziqlari: har chiziq `[x, y]` nuqtalar (0..1000 × 0..400, butun son).
typedef Strokes = List<List<List<int>>>;

/// Shu qurilmada imzo chizish (barmoq yoki pero). Nuqtalar butun sonlarga keltiriladi; tekshiruv
/// va SVG yadroda. Imzo qog'ozdagidek och fonda — PDF bilan bir xil ko'rinadi.
Future<Strokes?> drawSignature(BuildContext context, String name) =>
    showBarakaDialog<Strokes>(context, (_) => _SignatureDialog(name: name));

class _SignatureDialog extends StatefulWidget {
  const _SignatureDialog({required this.name});

  final String name;

  @override
  State<_SignatureDialog> createState() => _SignatureDialogState();
}

class _SignatureDialogState extends State<_SignatureDialog> {
  final Strokes _strokes = [];

  List<int> _point(Offset p, Size s) => [
    (p.dx / s.width * padW).clamp(0, padW).truncate(),
    (p.dy / s.height * padH).clamp(0, padH).truncate(),
  ];

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: Text(context.t('partnership.sign.title', {'name': widget.name})),
    content: SizedBox(
      width: 600,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Hint(context.t('partnership.sign.hint')),
          const SizedBox(height: 8),
          AspectRatio(
            aspectRatio: padW / padH,
            child: LayoutBuilder(
              builder: (context, box) => Semantics(
                label: context.t('partnership.sign.pad'),
                child: GestureDetector(
                  key: const Key('signature-pad'),
                  onPanStart: (d) => setState(() => _strokes.add([_point(d.localPosition, box.biggest)])),
                  onPanUpdate: (d) => setState(() => _strokes.last.add(_point(d.localPosition, box.biggest))),
                  child: CustomPaint(painter: _InkPainter(_strokes), size: box.biggest),
                ),
              ),
            ),
          ),
        ],
      ),
    ),
    actions: [
      TextButton(onPressed: () => setState(_strokes.clear), child: Text(context.t('partnership.sign.clear'))),
      TextButton(onPressed: () => Navigator.of(context).pop(), child: Text(context.t('common.cancel'))),
      FilledButton(
        onPressed: _strokes.isEmpty ? null : () => Navigator.of(context).pop(_strokes),
        child: Text(context.t('partnership.sign.save')),
      ),
    ],
  );
}

class _InkPainter extends CustomPainter {
  _InkPainter(this.strokes);

  final Strokes strokes;

  @override
  void paint(Canvas canvas, Size size) {
    final r = RRect.fromRectAndRadius(Offset.zero & size, const Radius.circular(8));
    canvas.drawRRect(r, Paint()..color = const Color(0xFFFAF9F5));
    final pen = Paint()
      ..color = const Color(0xFF1F1E1D)
      ..strokeWidth = 3
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round
      ..style = PaintingStyle.stroke;
    Offset at(List<int> p) => Offset(p[0] / padW * size.width, p[1] / padH * size.height);
    for (final s in strokes) {
      if (s.isEmpty) continue;
      final path = Path()..moveTo(at(s.first).dx, at(s.first).dy);
      for (final p in s.skip(1)) {
        path.lineTo(at(p).dx, at(p).dy);
      }
      canvas.drawPath(path, pen);
      if (s.length == 1) canvas.drawCircle(at(s.first), 1.5, pen);
    }
  }

  @override
  bool shouldRepaint(_InkPainter old) => true;
}
