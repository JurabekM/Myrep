import 'dart:async';

import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/theme/app_theme.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/features/content/data/content_providers.dart';
import 'package:baraka_daftari/features/content/domain/content.dart';
import 'package:baraka_daftari/features/content/presentation/chapter_screen.dart';
import 'package:baraka_daftari/features/content/presentation/content_widgets.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// «Daftar sahifasi»: foydalanuvchi qonunni o'z qo'li bilan yozadi
/// (qog'oz uslubida, chiziqli). `daftar_pages` jadvaliga saqlanadi.
class DaftarPageScreen extends ConsumerStatefulWidget {
  const DaftarPageScreen({required this.chapterId, super.key});

  final String chapterId;

  @override
  ConsumerState<DaftarPageScreen> createState() => _DaftarPageScreenState();
}

class _DaftarPageScreenState extends ConsumerState<DaftarPageScreen> {
  final _text = TextEditingController();
  bool _loaded = false;
  bool _saving = false;

  static const _lineHeight = 32.0;
  static const _top = 10.0;

  @override
  void initState() {
    super.initState();
    unawaited(_load());
  }

  @override
  void dispose() {
    _text.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final page = await (await ref.read(
        contentServiceProvider.future,
      )).daftarPage(widget.chapterId);
      _text.text = page?.body ?? '';
    } on Object {
      AppLog.event('daftar_load_failed');
    }
    if (mounted) setState(() => _loaded = true);
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    final l10n = context.l10n;
    final messenger = ScaffoldMessenger.of(context);
    final navigator = Navigator.of(context);
    try {
      final chapter = await ref.read(
        chapterByIdProvider(widget.chapterId).future,
      );
      if (chapter == null) throw StateError('bob yopiq');
      await (await ref.read(
        contentServiceProvider.future,
      )).saveDaftarPage(chapter, _text.text);
      ref.invalidate(hasDaftarPageProvider(widget.chapterId));
      await recordTaskEvent(ref, TaskTrigger.daftarPageWritten);
      messenger.showSnackBar(SnackBar(content: Text(l10n.daftarPageSaved)));
      navigator.pop();
    } on Object {
      AppLog.event('daftar_save_failed');
      messenger.showSnackBar(SnackBar(content: Text(l10n.genericError)));
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final lang = Localizations.localeOf(context).languageCode;
    final theme = Theme.of(context);
    final chapter = ref
        .watch(chapterByIdProvider(widget.chapterId))
        .valueOrNull;
    final dark = theme.brightness == Brightness.dark;
    final paper = dark
        ? DaftarColors.nightPaperRaised
        : DaftarColors.paperRaised;
    final rule = dark ? DaftarColors.nightRule : DaftarColors.rule;
    return Scaffold(
      appBar: AppBar(title: Text(l10n.daftarPageTitle)),
      body: !_loaded
          ? const Center(child: CircularProgressIndicator())
          : SafeArea(
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 620),
                  child: ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      if (chapter != null)
                        Text(
                          l10n.lawLabel(chapter.law.number),
                          style: theme.textTheme.titleMedium,
                        ),
                      Text(l10n.daftarPageHint),
                      const ContentDisclaimer(),
                      const SizedBox(height: 8),
                      // Qog'oz: chiziqlar matn qatorlariga mos.
                      DecoratedBox(
                        decoration: BoxDecoration(
                          color: paper,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: rule),
                        ),
                        child: CustomPaint(
                          painter: _RuledPaper(rule, _lineHeight, _top),
                          child: Padding(
                            padding: const EdgeInsets.fromLTRB(24, _top, 16, 8),
                            child: TextField(
                              key: const Key('daftar-text'),
                              controller: _text,
                              minLines: 10,
                              maxLines: null,
                              maxLength: 2000,
                              keyboardType: TextInputType.multiline,
                              style: theme.textTheme.bodyLarge?.copyWith(
                                height:
                                    _lineHeight /
                                    (theme.textTheme.bodyLarge?.fontSize ?? 17),
                                fontStyle: FontStyle.italic,
                              ),
                              // Ichki chekinish yo'q — qatorlar chiziqlarga
                              // aniq tushadi (qurilmada ko'rilgan siljish).
                              strutStyle: const StrutStyle(
                                height: 1,
                                fontSize: _lineHeight,
                                forceStrutHeight: true,
                              ),
                              decoration: InputDecoration(
                                isDense: true,
                                contentPadding: EdgeInsets.zero,
                                border: InputBorder.none,
                                hintText: chapter?.law.text.of(lang),
                                counterText: '',
                              ),
                              onChanged: (_) => setState(() {}),
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      FilledButton(
                        key: const Key('daftar-save'),
                        onPressed: _text.text.trim().isEmpty || _saving
                            ? null
                            : _save,
                        child: Text(l10n.save),
                      ),
                    ],
                  ),
                ),
              ),
            ),
    );
  }
}

class _RuledPaper extends CustomPainter {
  _RuledPaper(this.color, this.lineHeight, this.top);

  final Color color;
  final double lineHeight;

  /// Matnning yuqori chekinishi — chiziqlar har qator ostiga tushadi.
  final double top;

  @override
  void paint(Canvas canvas, Size size) {
    final line = Paint()
      ..color = color
      ..strokeWidth = 1;
    for (var y = top + lineHeight - 3; y < size.height; y += lineHeight) {
      canvas.drawLine(Offset(12, y), Offset(size.width - 12, y), line);
    }
    // Daftar hoshiyasi (chap tomonda).
    canvas.drawLine(
      const Offset(16, 0),
      Offset(16, size.height),
      Paint()
        ..color = color
        ..strokeWidth = 1.5,
    );
  }

  @override
  bool shouldRepaint(_RuledPaper old) =>
      old.color != color || old.lineHeight != lineHeight || old.top != top;
}
