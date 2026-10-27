import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/features/agreements/data/agreement_providers.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement.dart';
import 'package:baraka_daftari/features/agreements/presentation/accountability_actions.dart';
import 'package:baraka_daftari/features/partnerships/data/partnership_providers.dart';
import 'package:baraka_daftari/features/partnerships/domain/venture_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// «Katta foyda» dialogi natijasi (SPEC 2F.7).
enum ProfitSpikeOutcome {
  /// Ikkala tomon tasdiqladi — taqsimotni davom ettirish mumkin.
  distribute,

  /// Navbatdan tashqari ko'rik boshlandi.
  review,
}

/// Davr foydasi navbatdagidan sezilarli oshganda taqsimotdan oldin chiqadi:
/// har bir tomon 4–5-bandni qayta o'qiganini belgilaydi (SPEC 2F.7).
class ProfitSpikeDialog extends ConsumerStatefulWidget {
  const ProfitSpikeDialog({
    required this.partnershipId,
    required this.initial,
    super.key,
  });

  final String partnershipId;
  final ProfitSpikeCheck initial;

  @override
  ConsumerState<ProfitSpikeDialog> createState() => _ProfitSpikeDialogState();
}

class _ProfitSpikeDialogState extends ConsumerState<ProfitSpikeDialog> {
  late ProfitSpikeCheck _check = widget.initial;
  Agreement? _agreement;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _loadAgreement();
  }

  Future<void> _loadAgreement() async {
    final s = await ref.read(agreementServiceProvider.future);
    final a = await s.bySource(
      AgreementSource.partnership,
      widget.partnershipId,
    );
    if (mounted) setState(() => _agreement = a);
  }

  Future<void> _read(String partyId) async {
    final agreement = _agreement;
    if (agreement == null || _busy) return;
    setState(() => _busy = true);
    final ok = await runAccountability(
      context,
      ref,
      agreement.meta.id,
      (s) => s.acknowledgeSpike(
        agreement,
        partyId: partyId,
        key: _check.key,
      ),
    );
    final ledger = await ref.read(ventureLedgerServiceProvider.future);
    final p = await ledger.find(widget.partnershipId);
    if (ok && p != null) {
      final fresh = await ledger.spikeCheck(p);
      if (mounted) setState(() => _check = fresh);
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _review(BuildContext context) async {
    final agreement = _agreement;
    if (agreement == null) return;
    String? reviewId;
    final ok = await runAccountability(
      context,
      ref,
      agreement.meta.id,
      (s) async {
        reviewId = await s.openReview(agreement);
      },
    );
    if (ok && context.mounted && reviewId != null) {
      Navigator.pop(context, ProfitSpikeOutcome.review);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final money = context.money;
    final theme = Theme.of(context);
    return AlertDialog(
      key: const Key('spike-dialog'),
      title: Text(l10n.acSpikeTitle),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(l10n.acSpikeMessage),
            const SizedBox(height: 8),
            Text(
              l10n.acSpikeAmount(money(_check.actual)),
              style: theme.textTheme.titleSmall,
            ),
            const SizedBox(height: 8),
            for (final p in _check.parties)
              CheckboxListTile(
                key: Key('spike-party-${p.id}'),
                contentPadding: EdgeInsets.zero,
                value: _check.acked.contains(p.id),
                title: Text(l10n.acSpikeRead(p.name)),
                onChanged: _check.acked.contains(p.id) || _busy
                    ? null
                    : (_) => _read(p.id),
              ),
          ],
        ),
      ),
      actions: [
        TextButton(
          key: const Key('spike-later'),
          onPressed: () => Navigator.pop(context),
          child: Text(l10n.acSpikeCancel),
        ),
        OutlinedButton(
          key: const Key('spike-review'),
          onPressed: _agreement == null || _busy
              ? null
              : () => _review(context),
          child: Text(l10n.acSpikeReviewOffer),
        ),
        FilledButton(
          key: const Key('spike-distribute'),
          onPressed: _check.blocks
              ? null
              : () => Navigator.pop(context, ProfitSpikeOutcome.distribute),
          child: Text(l10n.acSpikeDistribute),
        ),
      ],
    );
  }
}
