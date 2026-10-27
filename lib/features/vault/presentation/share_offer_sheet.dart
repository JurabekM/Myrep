import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/refresh.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/features/content/data/content_providers.dart';
import 'package:baraka_daftari/features/content/domain/content.dart';
import 'package:baraka_daftari/features/income/domain/income.dart';
import 'package:baraka_daftari/features/vault/data/vault_providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Daromad saqlangach: «Shundan X so'm — kelajagingiz uchun».
/// [Ajratish] [Boshqa summa] [Bu safar emas].
Future<void> showShareOfferSheet(
  BuildContext context, {
  required Income income,
  required Money suggestion,
}) => showModalBottomSheet<void>(
  context: context,
  showDragHandle: true,
  builder: (_) => ShareOfferSheet(income: income, suggestion: suggestion),
);

class ShareOfferSheet extends ConsumerStatefulWidget {
  const ShareOfferSheet({
    required this.income,
    required this.suggestion,
    super.key,
  });

  final Income income;
  final Money suggestion;

  @override
  ConsumerState<ShareOfferSheet> createState() => _ShareOfferSheetState();
}

class _ShareOfferSheetState extends ConsumerState<ShareOfferSheet> {
  bool _busy = false;

  Future<void> _allocate(Money amount) async {
    setState(() => _busy = true);
    final l10n = context.l10n;
    final messenger = ScaffoldMessenger.of(context);
    final navigator = Navigator.of(context);
    final text = context.money(amount);
    try {
      final vault = await ref.read(vaultServiceProvider.future);
      await vault.allocateFromIncome(widget.income, amount);
      refreshMoneyViews(ref);
      await recordTaskEvent(ref, TaskTrigger.incomeShared);
      await recordTaskEvent(ref, TaskTrigger.vaultFirstDeposit);
      messenger.showSnackBar(SnackBar(content: Text(l10n.shareDone(text))));
      navigator.pop();
    } on Object {
      AppLog.event('share_allocate_failed');
      messenger.showSnackBar(SnackBar(content: Text(l10n.genericError)));
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _other() async {
    final amount = await showAmountSheet(
      context,
      currency: widget.suggestion.currency,
      title: context.l10n.shareOtherAmount,
      initial: widget.suggestion,
      max: widget.income.amount,
    );
    if (amount != null && mounted) await _allocate(amount);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(24, 0, 24, 16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              l10n.shareOfferTitle,
              style: theme.textTheme.titleLarge,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              l10n.shareOfferBody(context.money(widget.suggestion)),
              key: const Key('share-offer-text'),
              style: theme.textTheme.bodyLarge,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 4),
            Text(
              l10n.shareOfferHint,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 20),
            FilledButton(
              key: const Key('share-allocate'),
              onPressed: _busy ? null : () => _allocate(widget.suggestion),
              child: Text(l10n.shareAllocate),
            ),
            const SizedBox(height: 8),
            OutlinedButton(
              key: const Key('share-other'),
              onPressed: _busy ? null : _other,
              child: Text(l10n.shareOtherAmount),
            ),
            TextButton(
              key: const Key('share-skip'),
              onPressed: _busy
                  ? null
                  : () {
                      ScaffoldMessenger.of(context)
                        ..hideCurrentSnackBar()
                        ..showSnackBar(
                          SnackBar(content: Text(l10n.shareSkipped)),
                        );
                      Navigator.of(context).pop();
                    },
              child: Text(l10n.shareSkip),
            ),
          ],
        ),
      ),
    );
  }
}
