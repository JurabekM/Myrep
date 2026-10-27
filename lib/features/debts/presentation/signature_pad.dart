import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:flutter/material.dart';

/// Barmoq bilan chizilgan imzo chiziqlari.
class SignatureController extends ChangeNotifier {
  final List<List<Offset>> _strokes = [];

  List<List<Offset>> get strokes => _strokes;
  bool get isEmpty => _strokes.every((s) => s.length < 2);

  void start(Offset p) {
    _strokes.add([p]);
    notifyListeners();
  }

  void extend(Offset p) {
    if (_strokes.isEmpty) return;
    _strokes.last.add(p);
    notifyListeners();
  }

  void clear() {
    _strokes.clear();
    notifyListeners();
  }

  /// Imzoni shaffof fonli PNG'ga ([size] — chizish maydoni o'lchami).
  Future<Uint8List> toPng(Size size, {double pixelRatio = 2}) async {
    final recorder = ui.PictureRecorder();
    final canvas = Canvas(recorder)..scale(pixelRatio);
    _paintStrokes(canvas, _strokes, const Color(0xFF1F2A44));
    final image = await recorder.endRecording().toImage(
      (size.width * pixelRatio).ceil(),
      (size.height * pixelRatio).ceil(),
    );
    final data = await image.toByteData(format: ui.ImageByteFormat.png);
    image.dispose();
    return data!.buffer.asUint8List();
  }
}

void _paintStrokes(Canvas canvas, List<List<Offset>> strokes, Color color) {
  final paint = Paint()
    ..color = color
    ..strokeWidth = 2.6
    ..strokeCap = StrokeCap.round
    ..strokeJoin = StrokeJoin.round
    ..style = PaintingStyle.stroke;
  for (final s in strokes) {
    if (s.length < 2) continue;
    final path = Path()..moveTo(s.first.dx, s.first.dy);
    for (final p in s.skip(1)) {
      path.lineTo(p.dx, p.dy);
    }
    canvas.drawPath(path, paint);
  }
}

/// Imzo chizish maydoni.
class SignaturePad extends StatelessWidget {
  const SignaturePad({required this.controller, super.key});

  final SignatureController controller;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return DecoratedBox(
      decoration: BoxDecoration(
        color: scheme.surfaceContainerLowest,
        border: Border.all(color: scheme.outline),
        borderRadius: BorderRadius.circular(12),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(12),
        child: GestureDetector(
          onPanStart: (d) => controller.start(d.localPosition),
          onPanUpdate: (d) => controller.extend(d.localPosition),
          child: ListenableBuilder(
            listenable: controller,
            builder: (context, _) => CustomPaint(
              painter: _SignaturePainter(controller.strokes, scheme.onSurface),
              size: Size.infinite,
            ),
          ),
        ),
      ),
    );
  }
}

class _SignaturePainter extends CustomPainter {
  _SignaturePainter(this.strokes, this.color);

  final List<List<Offset>> strokes;
  final Color color;

  @override
  void paint(Canvas canvas, Size size) => _paintStrokes(canvas, strokes, color);

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}

/// Imzolash oynasi: ism (tahrirlanadi) va imzo. Natija — (ism, PNG).
Future<(String, Uint8List)?> showSignDialog(
  BuildContext context, {
  required String role,
  required String name,
}) => Navigator.of(context).push<(String, Uint8List)>(
  MaterialPageRoute(
    fullscreenDialog: true,
    builder: (_) => _SignScreen(role: role, name: name),
  ),
);

class _SignScreen extends StatefulWidget {
  const _SignScreen({required this.role, required this.name});

  final String role;
  final String name;

  @override
  State<_SignScreen> createState() => _SignScreenState();
}

class _SignScreenState extends State<_SignScreen> {
  late final TextEditingController _name = TextEditingController(
    text: widget.name,
  );
  final _pad = SignatureController();
  final GlobalKey _padKey = GlobalKey();

  @override
  void initState() {
    super.initState();
    _pad.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    _name.dispose();
    _pad.dispose();
    super.dispose();
  }

  Future<void> _done() async {
    final box = _padKey.currentContext!.findRenderObject()! as RenderBox;
    final png = await _pad.toPng(box.size);
    if (mounted) Navigator.pop(context, (_name.text.trim(), png));
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final ready = !_pad.isEmpty && _name.text.trim().isNotEmpty;
    return Scaffold(
      appBar: AppBar(title: Text(l10n.signTitle(widget.role))),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextField(
              key: const Key('sign-name'),
              controller: _name,
              decoration: InputDecoration(labelText: l10n.memberName),
              onChanged: (_) => setState(() {}),
            ),
            const SizedBox(height: 12),
            Text(l10n.signHere),
            const SizedBox(height: 8),
            Expanded(
              child: SignaturePad(key: _padKey, controller: _pad),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                TextButton(
                  key: const Key('sign-clear'),
                  onPressed: _pad.clear,
                  child: Text(l10n.signClear),
                ),
                const Spacer(),
                FilledButton(
                  key: const Key('sign-done'),
                  onPressed: ready ? _done : null,
                  child: Text(l10n.signAction),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
