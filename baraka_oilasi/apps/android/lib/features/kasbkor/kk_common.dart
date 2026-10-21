import 'package:flutter/material.dart';

import '../../app/i18n.dart';
import '../../app/theme.dart';
import '../../shared/widgets.dart';

/// Kasb-kor hamyonlari: naqd kassa va karta.
const kkWallets = ['CASH', 'CARD'];

/// Hamyon tanlovi (naqd / karta).
class KkWalletPicker extends StatelessWidget {
  const KkWalletPicker({required this.label, required this.value, required this.onChanged, super.key});

  final String label;
  final String value;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) => SegmentedChoice<String>(
    label: label,
    options: [for (final w in kkWallets) (w, context.t('kk.wallet.$w'))],
    value: value,
    onChanged: onChanged,
  );
}

/// Pastdan ochiladigan forma sarlavhasi (va ixtiyoriy izoh).
class KkSheetTitle extends StatelessWidget {
  const KkSheetTitle(this.title, {this.hint, super.key});

  final String title;
  final String? hint;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      Semantics(
        header: true,
        child: Text(title, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700)),
      ),
      if (hint != null) ...[const SizedBox(height: 6), Hint(hint!)],
      const SizedBox(height: 16),
    ],
  );
}

/// Ko'rsatkich kartasi: yorliq, katta summa, izohlar va ixtiyoriy «o'tish» tugmasi.
class KkFigureCard extends StatelessWidget {
  const KkFigureCard({
    required this.label,
    required this.value,
    this.lines = const [],
    this.action,
    this.onAction,
    this.warn = false,
    this.valueKey,
    super.key,
  });

  final String label;
  final String value;

  /// Qo'shimcha qatorlar: matn va ogohlantirish belgisi.
  final List<(String, bool)> lines;
  final String? action;
  final VoidCallback? onAction;
  final bool warn;
  final Key? valueKey;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return Card(
      shape: warn
          ? RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
              side: BorderSide(color: p.warn),
            )
          : null,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(label, style: TextStyle(color: p.inkMuted, fontSize: 14)),
            const SizedBox(height: 4),
            Text(
              value,
              key: valueKey,
              style: const TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.w700,
                fontFeatures: [FontFeature.tabularFigures()],
              ),
            ),
            for (final (text, isWarn) in lines)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text(
                  text,
                  style: TextStyle(color: isWarn ? p.warn : p.inkMuted, fontSize: 14),
                ),
              ),
            if (action != null) ...[
              const SizedBox(height: 8),
              Align(
                alignment: Alignment.centerLeft,
                child: OutlinedButton(onPressed: onAction, child: Text(action!)),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

/// Asosiy (to'ldirilgan) yoki ikkinchi darajali (chegarali) tugma.
Widget kkButton({required bool primary, required VoidCallback? onPressed, required String label}) => primary
    ? FilledButton(onPressed: onPressed, child: Text(label))
    : OutlinedButton(onPressed: onPressed, child: Text(label));

/// Matn summasi manfiymi (`MoneyDto.minor` belgisi) — faqat rang tanlash uchun, hisob emas.
bool kkNegative(String minor) => minor.startsWith('-');
