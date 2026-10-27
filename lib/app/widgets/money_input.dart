import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/money/money_format.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

extension MoneyFormatContext on BuildContext {
  /// Joriy tilga mos ko'rinish: `8 000 000 so'm` / `8 000 000 сум`.
  String money(Money m) => MoneyFormatter.format(
    m,
    languageCode: Localizations.localeOf(this).languageCode,
  );
}

/// Butun major birlikdagi (so'm) summa kiritish holati. Kiritish faqat
/// butun so'mda (tiyin amalda ishlatilmaydi).
class AmountController extends ValueNotifier<int> {
  AmountController([super.value = 0]);

  /// 999 999 999 999 so'mgacha — toshib ketmaydi.
  static const maxDigits = 12;

  void appendDigits(String digits) {
    final next = value == 0 ? digits : '$value$digits';
    final trimmed = next.replaceFirst(RegExp('^0+(?=.)'), '');
    if (trimmed.length > maxDigits) return;
    value = int.parse(trimmed);
  }

  void backspace() {
    final s = value.toString();
    value = s.length <= 1 ? 0 : int.parse(s.substring(0, s.length - 1));
  }

  Money moneyIn(CurrencyCode currency) => Money.major(value, currency);
}

/// Bir qo'l bilan ishlatiladigan raqamli klaviatura (tizim klaviaturasisiz).
class MoneyKeypad extends StatelessWidget {
  const MoneyKeypad({required this.controller, super.key});

  final AmountController controller;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    Widget key(String label, {Key? key, VoidCallback? onTap, Widget? child}) =>
        Expanded(
          child: Padding(
            padding: const EdgeInsets.all(4),
            child: SizedBox(
              height: 56,
              child: OutlinedButton(
                key: key,
                onPressed: () {
                  HapticFeedback.selectionClick();
                  (onTap ?? () => controller.appendDigits(label))();
                },
                child:
                    child ?? Text(label, style: const TextStyle(fontSize: 22)),
              ),
            ),
          ),
        );

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        for (final row in const [
          ['1', '2', '3'],
          ['4', '5', '6'],
          ['7', '8', '9'],
        ])
          Row(
            children: [for (final d in row) key(d, key: Key('amount-key-$d'))],
          ),
        Row(
          children: [
            key('000', key: const Key('amount-key-000')),
            key('0', key: const Key('amount-key-0')),
            key(
              '',
              key: const Key('amount-key-back'),
              onTap: controller.backspace,
              child: Semantics(
                label: l10n.keypadDelete,
                child: const Icon(Icons.backspace_outlined),
              ),
            ),
          ],
        ),
      ],
    );
  }
}

/// Katta summa ko'rinishi (formatlangan).
class AmountDisplay extends StatelessWidget {
  const AmountDisplay({
    required this.controller,
    required this.currency,
    super.key,
  });

  final AmountController controller;
  final CurrencyCode currency;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return ValueListenableBuilder<int>(
      valueListenable: controller,
      builder: (context, value, _) => FittedBox(
        fit: BoxFit.scaleDown,
        child: Text(
          context.money(Money.major(value, currency)),
          key: const Key('amount-display'),
          style: theme.textTheme.displaySmall?.copyWith(
            color: value == 0
                ? theme.colorScheme.onSurfaceVariant
                : theme.colorScheme.onSurface,
          ),
        ),
      ),
    );
  }
}

/// Summa so'raydigan oyna (pastki panel). `null` — bekor qilindi.
Future<Money?> showAmountSheet(
  BuildContext context, {
  required CurrencyCode currency,
  String? title,
  Money? initial,
  Money? max,
}) => showModalBottomSheet<Money>(
  context: context,
  isScrollControlled: true,
  showDragHandle: true,
  builder: (context) => _AmountSheet(
    currency: currency,
    title: title,
    initial: initial,
    max: max,
  ),
);

class _AmountSheet extends StatefulWidget {
  const _AmountSheet({
    required this.currency,
    this.title,
    this.initial,
    this.max,
  });

  final CurrencyCode currency;
  final String? title;
  final Money? initial;
  final Money? max;

  @override
  State<_AmountSheet> createState() => _AmountSheetState();
}

class _AmountSheetState extends State<_AmountSheet> {
  late final AmountController _amount = AmountController(
    (widget.initial?.minorUnits ?? 0) ~/ widget.currency.minorPerMajor,
  );

  @override
  void dispose() {
    _amount.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              widget.title ?? l10n.amountDialogTitle,
              style: Theme.of(context).textTheme.titleMedium,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Center(
              child: AmountDisplay(
                controller: _amount,
                currency: widget.currency,
              ),
            ),
            const SizedBox(height: 12),
            MoneyKeypad(controller: _amount),
            const SizedBox(height: 12),
            ValueListenableBuilder<int>(
              valueListenable: _amount,
              builder: (context, value, _) {
                final money = Money.major(value, widget.currency);
                final ok =
                    value > 0 && (widget.max == null || money <= widget.max!);
                return FilledButton(
                  key: const Key('amount-sheet-done'),
                  onPressed: ok ? () => Navigator.of(context).pop(money) : null,
                  child: Text(l10n.amountDialogDone),
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}
