import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../app/i18n.dart';
import '../app/theme.dart';
import '../core/core.dart';

/// Yadro xatosi matni (`error.<CODE>`), ekran o'quvchi uchun «alert» sifatida.
class ErrorText extends StatelessWidget {
  const ErrorText(this.error, {super.key});

  final Object? error;

  @override
  Widget build(BuildContext context) {
    if (error == null) return const SizedBox.shrink();
    final tr = context.tr;
    return Semantics(
      liveRegion: true,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Text(tr(errorKey(error, tr.has)), style: TextStyle(color: context.palette.danger)),
      ),
    );
  }
}

/// `AsyncValue` ni ko'rsatish: yuklanmoqda — indikator, xato — matn, tayyor — `data`.
class AsyncView<T> extends StatelessWidget {
  const AsyncView({required this.value, required this.data, super.key});

  final AsyncValue<T> value;
  final Widget Function(T data) data;

  @override
  Widget build(BuildContext context) => value.when(
    data: data,
    // Qayta o'qishda eski ma'lumot ko'rinib turadi (`skipLoadingOnRefresh`).
    loading: () => const Padding(
      padding: EdgeInsets.all(24),
      child: Center(child: CircularProgressIndicator()),
    ),
    error: (e, _) => Padding(padding: const EdgeInsets.all(16), child: ErrorText(e)),
  );
}

/// Karta: sarlavha (ixtiyoriy) va mazmun.
class SectionCard extends StatelessWidget {
  const SectionCard({required this.children, this.title, this.trailing, this.semanticLabel, super.key});

  final String? title;
  final Widget? trailing;
  final List<Widget> children;
  final String? semanticLabel;

  @override
  Widget build(BuildContext context) {
    final card = Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (title != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Row(
                  children: [
                    Expanded(
                      child: Semantics(
                        header: true,
                        child: Text(title!, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                      ),
                    ),
                    ?trailing,
                  ],
                ),
              ),
            ...children,
          ],
        ),
      ),
    );
    return semanticLabel == null ? card : Semantics(container: true, label: semanticLabel, child: card);
  }
}

/// Katta raqamli ko'rsatkich (KPI).
class Kpi extends StatelessWidget {
  const Kpi({required this.label, required this.value, this.hint, this.accent = false, super.key});

  final String label;
  final String value;
  final String? hint;
  final bool accent;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: TextStyle(color: p.inkMuted, fontSize: 14)),
            const SizedBox(height: 6),
            Text(
              value,
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.w700,
                color: accent ? p.accent : p.ink,
                fontFeatures: const [FontFeature.tabularFigures()],
              ),
            ),
            if (hint != null) ...[
              const SizedBox(height: 4),
              Text(hint!, style: TextStyle(color: p.inkMuted, fontSize: 13)),
            ],
          ],
        ),
      ),
    );
  }
}

/// Matn maydoni (yorliq bilan).
class Field extends StatelessWidget {
  const Field({
    required this.label,
    required this.controller,
    this.hint,
    this.keyboardType,
    this.obscure = false,
    this.maxLength,
    this.autofocus = false,
    this.onChanged,
    this.inputFormatters,
    this.textAlign = TextAlign.start,
    this.style,
    this.maxLines = 1,
    super.key,
  });

  final String label;
  final TextEditingController controller;
  final String? hint;
  final TextInputType? keyboardType;
  final bool obscure;
  final int? maxLength;
  final bool autofocus;
  final ValueChanged<String>? onChanged;
  final List<TextInputFormatter>? inputFormatters;
  final TextAlign textAlign;
  final TextStyle? style;
  final int maxLines;

  @override
  Widget build(BuildContext context) => TextField(
    controller: controller,
    keyboardType: keyboardType,
    obscureText: obscure,
    maxLength: maxLength,
    autofocus: autofocus,
    onChanged: onChanged,
    inputFormatters: inputFormatters,
    textAlign: textAlign,
    style: style,
    maxLines: obscure ? 1 : maxLines,
    decoration: InputDecoration(labelText: label, hintText: hint, counterText: ''),
  );
}

/// Summa: matn sifatida qoladi va yadroda parse qilinadi (UI hisoblamaydi).
class AmountField extends StatelessWidget {
  const AmountField({required this.label, required this.controller, this.hint, this.autofocus = false, super.key});

  final String label;
  final TextEditingController controller;
  final String? hint;
  final bool autofocus;

  @override
  Widget build(BuildContext context) => Field(
    label: label,
    controller: controller,
    hint: hint,
    autofocus: autofocus,
    keyboardType: const TextInputType.numberWithOptions(decimal: true),
    style: const TextStyle(fontSize: 18, fontFeatures: [FontFeature.tabularFigures()]),
  );
}

/// PIN: 6 raqam, yashirin.
class PinField extends StatelessWidget {
  const PinField({required this.label, required this.controller, this.autofocus = false, this.onChanged, super.key});

  final String label;
  final TextEditingController controller;
  final bool autofocus;
  final ValueChanged<String>? onChanged;

  @override
  Widget build(BuildContext context) => Field(
    label: label,
    controller: controller,
    obscure: true,
    maxLength: 6,
    autofocus: autofocus,
    onChanged: onChanged,
    keyboardType: TextInputType.number,
    inputFormatters: [FilteringTextInputFormatter.digitsOnly],
    textAlign: TextAlign.center,
    style: const TextStyle(fontSize: 24, letterSpacing: 12),
  );
}

/// Variant kartasi (radio): sarlavha va izoh, tanlangani aksent chegarali.
class ChoiceTile extends StatelessWidget {
  const ChoiceTile({required this.label, required this.selected, required this.onTap, this.hint, super.key});

  final String label;
  final String? hint;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Semantics(
        inMutuallyExclusiveGroup: true,
        checked: selected,
        button: true,
        label: label,
        hint: hint,
        excludeSemantics: true,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(10),
          child: Container(
            constraints: const BoxConstraints(minHeight: 48),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: selected ? p.surface : null,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: selected ? p.accent : p.fieldLine, width: selected ? 2 : 1),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(
                  selected ? Icons.radio_button_checked : Icons.radio_button_off,
                  color: selected ? p.accent : p.inkMuted,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(label, style: const TextStyle(fontWeight: FontWeight.w700)),
                      if (hint != null) Text(hint!, style: TextStyle(color: p.inkMuted, fontSize: 14)),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Ha / Yo'q / Bilmayman kabi bir qatorli tanlov.
class SegmentedChoice<T> extends StatelessWidget {
  const SegmentedChoice({
    required this.label,
    required this.options,
    required this.value,
    required this.onChanged,
    super.key,
  });

  final String label;
  final List<(T, String)> options;
  final T? value;
  final ValueChanged<T> onChanged;

  @override
  Widget build(BuildContext context) => Semantics(
    container: true,
    label: label,
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (label.isNotEmpty) ...[Text(label), const SizedBox(height: 6)],
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            for (final (v, text) in options)
              ChoiceChip(label: Text(text), selected: v == value, onSelected: (_) => onChanged(v)),
          ],
        ),
      ],
    ),
  );
}

/// Sobir hoji maslahati (desktop'dagi o'ng panel): ekran pastida yig'iladigan karta.
class MentorCard extends StatelessWidget {
  const MentorCard(this.tipKey, {super.key});

  final String tipKey;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return Semantics(
      container: true,
      label: context.t('mentor.name'),
      child: Card(
        color: p.sidebar,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                context.t('mentor.name'),
                style: TextStyle(color: p.accentText, fontWeight: FontWeight.w700, fontSize: 14),
              ),
              const SizedBox(height: 6),
              Text(context.t(tipKey), style: const TextStyle(height: 1.4)),
              const SizedBox(height: 12),
              Text(context.t('app.disclaimer'), style: TextStyle(color: p.inkMuted, fontSize: 12)),
            ],
          ),
        ),
      ),
    );
  }
}

/// Bir martalik amal holati (desktop'dagi `useMutation`): band, xato.
mixin ActionState<W extends StatefulWidget> on State<W> {
  bool busy = false;
  Object? error;

  /// `fn` ni bajaradi; xato bo'lsa — `error` ga yozadi va `null` qaytaradi.
  Future<T?> act<T>(Future<T> Function() fn) async {
    setState(() {
      busy = true;
      error = null;
    });
    try {
      return await fn();
    } on Object catch (e) {
      if (mounted) setState(() => error = e);
      return null;
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }
}

/// Ekran tanasi: aylanadigan ustun, 16 dp chekka. `ListView` emas — ekrandan chiqqan kartalar
/// (va ulardagi to'ldirilayotgan formalar) yo'q qilinmasin.
class ScreenBody extends StatelessWidget {
  const ScreenBody({required this.children, this.mentorKey, super.key});

  final List<Widget> children;
  final String? mentorKey;

  @override
  Widget build(BuildContext context) => SingleChildScrollView(
    padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (final c in children) Padding(padding: const EdgeInsets.only(bottom: 12), child: c),
        if (mentorKey != null) MentorCard(mentorKey!),
      ],
    ),
  );
}

/// Dialog overlay — qora 60 % (CLAUDE.md).
const barrier = Color(0x99000000);

Future<T?> showBarakaDialog<T>(BuildContext context, WidgetBuilder builder) =>
    showDialog<T>(context: context, barrierColor: barrier, builder: builder);

/// Pastdan ochiladigan forma (telefon uchun dialog o'rniga): klaviatura ustida, aylanadi.
Future<T?> showSheet<T>(BuildContext context, WidgetBuilder builder) => showModalBottomSheet<T>(
  context: context,
  barrierColor: barrier,
  isScrollControlled: true,
  useSafeArea: true,
  showDragHandle: true,
  builder: (ctx) => Padding(
    padding: EdgeInsets.only(bottom: MediaQuery.of(ctx).viewInsets.bottom),
    child: builder(ctx),
  ),
);

/// Ochiladigan ro'yxat (yorliq bilan). `value == null` — hali tanlanmagan.
class Select<T> extends StatelessWidget {
  const Select({required this.label, required this.items, required this.value, required this.onChanged, super.key});

  final String label;
  final List<(T, String)> items;
  final T? value;
  final ValueChanged<T?>? onChanged;

  @override
  Widget build(BuildContext context) => DropdownButtonFormField<T>(
    // Qiymat ro'yxatda bo'lmasa (masalan, yangilanayotganda) — tanlanmagan holat.
    initialValue: items.any((i) => i.$1 == value) ? value : null,
    key: ValueKey('$label:$value:${items.length}'),
    isExpanded: true,
    decoration: InputDecoration(labelText: label),
    items: [
      for (final (v, text) in items)
        DropdownMenuItem(
          value: v,
          child: Text(text, overflow: TextOverflow.ellipsis),
        ),
    ],
    onChanged: onChanged,
  );
}

/// Yorliq — qiymat qatori (hisobot jadvallari uchun).
class ValueRow extends StatelessWidget {
  const ValueRow(this.label, this.value, {this.strong = false, this.valueColor, super.key});

  final String label;
  final String value;
  final bool strong;
  final Color? valueColor;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 6),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(child: Text(label)),
        const SizedBox(width: 12),
        Text(
          value,
          textAlign: TextAlign.end,
          style: TextStyle(
            fontWeight: strong ? FontWeight.w700 : null,
            color: valueColor,
            fontFeatures: const [FontFeature.tabularFigures()],
          ),
        ),
      ],
    ),
  );
}

/// Ikkinchi darajali (muted) izoh matni.
class Hint extends StatelessWidget {
  const Hint(this.text, {this.color, super.key});

  final String text;
  final Color? color;

  @override
  Widget build(BuildContext context) =>
      Text(text, style: TextStyle(color: color ?? context.palette.inkMuted, fontSize: 14, height: 1.35));
}

/// Sana maydoni (`YYYY-MM-DD`): kalendar orqali tanlanadi, bo'sh bo'lishi mumkin.
class DateField extends StatelessWidget {
  const DateField({
    required this.label,
    required this.value,
    required this.onChanged,
    this.allowClear = true,
    super.key,
  });

  final String label;
  final String? value;
  final ValueChanged<String?> onChanged;
  final bool allowClear;

  @override
  Widget build(BuildContext context) {
    final shown = value == null ? '' : _show(value!);
    return InkWell(
      onTap: () async {
        final now = DateTime.now();
        final picked = await showDatePicker(
          context: context,
          initialDate: DateTime.tryParse(value ?? '') ?? now,
          firstDate: DateTime(now.year - 30),
          lastDate: DateTime(now.year + 30),
          barrierColor: barrier,
        );
        if (picked != null) {
          onChanged(
            '${picked.year}-${picked.month.toString().padLeft(2, '0')}-${picked.day.toString().padLeft(2, '0')}',
          );
        }
      },
      child: InputDecorator(
        decoration: InputDecoration(
          labelText: label,
          suffixIcon: value != null && allowClear
              ? IconButton(
                  icon: const Icon(Icons.clear),
                  tooltip: context.t('common.clear'),
                  onPressed: () => onChanged(null),
                )
              : const Icon(Icons.calendar_today_outlined),
        ),
        isEmpty: shown.isEmpty,
        child: Text(shown),
      ),
    );
  }

  static String _show(String iso) {
    final p = iso.split('-');
    return p.length == 3 ? '${p[2]}.${p[1]}.${p[0]}' : iso;
  }
}

/// Batafsil ekran (sheriklik, marosim va h.k.): o'z sarlavhasi va «orqaga» tugmasi bilan.
/// Qulflanganda yo'nalish o'zgaradi va bu sahifa ham yopiladi.
Future<void> pushScreen(BuildContext context, String title, WidgetBuilder builder) => Navigator.of(context).push(
  MaterialPageRoute<void>(
    builder: (ctx) => Scaffold(
      appBar: AppBar(title: Text(title)),
      body: builder(ctx),
    ),
  ),
);
