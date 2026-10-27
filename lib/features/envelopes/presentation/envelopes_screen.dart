import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/refresh.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/features/content/data/content_providers.dart';
import 'package:baraka_daftari/features/content/domain/content.dart';
import 'package:baraka_daftari/features/envelopes/data/envelope_providers.dart';
import 'package:baraka_daftari/features/envelopes/domain/envelope.dart';
import 'package:baraka_daftari/features/envelopes/domain/envelope_service.dart';
import 'package:baraka_daftari/features/expenses/domain/expense.dart';
import 'package:baraka_daftari/features/expenses/presentation/expense_views.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Haftalik konvertlar (SPEC 2B.6).
class EnvelopesScreen extends ConsumerWidget {
  const EnvelopesScreen({super.key});

  Future<void> _create(BuildContext context, WidgetRef ref) async {
    // `read(...).valueOrNull` kuzatilmagan provider uchun doim null —
    // `.future` kutiladi.
    final categories = await ref.read(expenseCategoriesProvider.future);
    if (!context.mounted) return;
    final draft = await showDialog<_Draft>(
      context: context,
      builder: (_) => _CreateDialog(categories: categories),
    );
    if (draft == null || !context.mounted) return;
    final limit = await showAmountSheet(
      context,
      currency: CurrencyCode.uzs,
      title: context.l10n.envelopeLimitTitle,
    );
    if (limit == null || !limit.isPositive) return;
    try {
      await (await ref.read(envelopeServiceProvider.future)).create(
        title: draft.title,
        weeklyLimit: limit,
        isCash: draft.isCash,
        categoryIds: draft.categoryIds,
      );
      refreshMoneyViews(ref);
      await recordTaskEvent(ref, TaskTrigger.envelopeCreated);
    } on Object {
      AppLog.event('envelope_create_failed');
    }
  }

  Future<void> _close(
    BuildContext context,
    WidgetRef ref,
    EnvelopePeriod p,
  ) async {
    final l10n = context.l10n;
    final messenger = ScaffoldMessenger.of(context);
    final money = context.money;
    final leftover = await showAmountSheet(
      context,
      currency: p.limit.currency,
      title: l10n.envelopeClosePrompt,
    );
    if (leftover == null) return;
    try {
      await (await ref.read(
        envelopeServiceProvider.future,
      )).closeWithLeftover(p, leftover);
      refreshMoneyViews(ref);
      messenger.showSnackBar(
        SnackBar(content: Text(l10n.envelopeClosed(money(leftover)))),
      );
    } on Object {
      AppLog.event('envelope_close_failed');
      messenger.showSnackBar(SnackBar(content: Text(l10n.genericError)));
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final status = ref.watch(envelopeStatusProvider);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.envelopesTitle)),
      floatingActionButton: FloatingActionButton.extended(
        key: const Key('envelope-add'),
        icon: const Icon(Icons.add),
        label: Text(l10n.envelopeAdd),
        onPressed: () => _create(context, ref),
      ),
      body: switch (status) {
        AsyncData(:final value) when value.isEmpty => Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text(l10n.envelopesEmpty, textAlign: TextAlign.center),
          ),
        ),
        AsyncData(:final value) => ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 96),
          children: [
            Text(l10n.envelopesHint),
            const SizedBox(height: 8),
            for (final s in value)
              _EnvelopeCard(
                status: s,
                onClose: (p) => _close(context, ref, p),
              ),
          ],
        ),
        AsyncError() => Center(child: Text(l10n.genericError)),
        _ => const Center(child: CircularProgressIndicator()),
      },
    );
  }
}

class _EnvelopeCard extends StatelessWidget {
  const _EnvelopeCard({required this.status, required this.onClose});

  final EnvelopeStatus status;
  final ValueChanged<EnvelopePeriod> onClose;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final money = context.money;
    final e = status.envelope;
    final w = status.current;
    final ratio = w.limit.isZero
        ? 0.0
        : (w.spent.minorUnits / w.limit.minorUnits).clamp(0, 1).toDouble();
    return Card(
      key: Key('envelope-${e.meta.id}'),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  e.isCash ? Icons.mail_outline : Icons.credit_card,
                  size: 20,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(e.title, style: theme.textTheme.titleMedium),
                ),
              ],
            ),
            const SizedBox(height: 8),
            LinearProgressIndicator(
              value: ratio,
              minHeight: 8,
              borderRadius: BorderRadius.circular(4),
              color: theme.colorScheme.tertiary,
              backgroundColor: theme.colorScheme.surfaceContainerHighest,
            ),
            const SizedBox(height: 6),
            Text(
              l10n.envelopeLine(
                money(w.spent),
                money(w.limit),
                money(w.computedLeftover),
              ),
              key: Key('envelope-line-${e.meta.id}'),
            ),
            if (w.isOver)
              Text(
                l10n.envelopeOver(money(w.spent - w.limit)),
                style: TextStyle(color: theme.colorScheme.tertiary),
              ),
            if (e.isCash)
              Text(
                l10n.envelopePutCash(money(w.limit)),
                style: theme.textTheme.bodySmall,
              ),
            for (final p in status.pendingClose) ...[
              const Divider(),
              Text(
                l10n.envelopeCloseTitle(
                  e.title,
                  '${formatDate(p.weekStart)} – '
                  '${formatDate(p.weekStart.plusDays(6))}',
                ),
              ),
              Align(
                alignment: Alignment.centerRight,
                child: FilledButton.tonal(
                  key: Key('envelope-close-${p.meta.id}'),
                  onPressed: () => onClose(p),
                  child: Text(l10n.envelopeCloseAction),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

typedef _Draft = ({String title, bool isCash, List<String> categoryIds});

class _CreateDialog extends StatefulWidget {
  const _CreateDialog({required this.categories});

  final List<Category> categories;

  @override
  State<_CreateDialog> createState() => _CreateDialogState();
}

class _CreateDialogState extends State<_CreateDialog> {
  final _title = TextEditingController();
  bool _cash = true;
  final _selected = <String>{};

  @override
  void dispose() {
    _title.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return AlertDialog(
      title: Text(l10n.envelopeAdd),
      scrollable: true,
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TextField(
            key: const Key('envelope-title'),
            controller: _title,
            autofocus: true,
            decoration: InputDecoration(labelText: l10n.titleLabel),
            onChanged: (_) => setState(() {}),
          ),
          SwitchListTile(
            key: const Key('envelope-cash'),
            contentPadding: EdgeInsets.zero,
            title: Text(l10n.envelopeCashMode),
            value: _cash,
            onChanged: (v) => setState(() => _cash = v),
          ),
          Text(l10n.envelopeCategories),
          const SizedBox(height: 4),
          Wrap(
            spacing: 6,
            runSpacing: 4,
            children: [
              for (final c in widget.categories)
                FilterChip(
                  key: Key('envelope-cat-${c.systemKey?.name ?? c.meta.id}'),
                  label: Text(l10n.category(c)),
                  selected: _selected.contains(c.meta.id),
                  onSelected: (on) => setState(
                    () => on
                        ? _selected.add(c.meta.id)
                        : _selected.remove(c.meta.id),
                  ),
                ),
            ],
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text(l10n.cancel),
        ),
        FilledButton(
          key: const Key('envelope-next'),
          onPressed: _title.text.trim().isEmpty
              ? null
              : () => Navigator.pop<_Draft>(context, (
                  title: _title.text.trim(),
                  isCash: _cash,
                  categoryIds: _selected.toList(),
                )),
          child: Text(l10n.save),
        ),
      ],
    );
  }
}
