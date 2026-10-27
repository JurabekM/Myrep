import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/refresh.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/obligations/data/obligation_providers.dart';
import 'package:baraka_daftari/features/obligations/domain/obligation.dart';
import 'package:baraka_daftari/features/obligations/domain/obligation_service.dart';
import 'package:baraka_daftari/features/obligations/presentation/obligation_views.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Nasiya daftari: do'kondagi qarzlar (`Debt`, `creditorType = SHOP`).
class NasiyaScreen extends ConsumerWidget {
  const NasiyaScreen({super.key});

  Future<void> _run(
    BuildContext context,
    WidgetRef ref,
    Future<void> Function(ObligationService) action,
  ) async {
    final messenger = ScaffoldMessenger.of(context);
    final error = context.l10n.genericError;
    try {
      await action(await ref.read(obligationServiceProvider.future));
      refreshMoneyViews(ref);
    } on Object {
      AppLog.event('nasiya_action_failed');
      messenger.showSnackBar(SnackBar(content: Text(error)));
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final list = ref.watch(nasiyaListProvider);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.sectionNasiya)),
      floatingActionButton: FloatingActionButton.extended(
        key: const Key('nasiya-add'),
        icon: const Icon(Icons.add),
        label: Text(l10n.nasiyaAdd),
        onPressed: () async {
          final ok = await showModalBottomSheet<bool>(
            context: context,
            isScrollControlled: true,
            showDragHandle: true,
            builder: (_) => const _NasiyaForm(),
          );
          if (ok ?? false) refreshMoneyViews(ref);
        },
      ),
      body: switch (list) {
        AsyncError() => Center(child: Text(l10n.genericError)),
        AsyncData(:final value) when value.isEmpty => Padding(
          padding: const EdgeInsets.all(24),
          child: Center(
            child: Text(l10n.nasiyaEmpty, textAlign: TextAlign.center),
          ),
        ),
        AsyncData(:final value) => ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 96),
          children: [
            Text(
              l10n.nasiyaTotal(
                context.money(
                  Money.sum(
                    value.map((d) => d.remaining),
                    value.first.remaining.currency,
                  ),
                ),
              ),
              key: const Key('nasiya-total'),
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            for (final d in value) _NasiyaCard(d, run: _run),
          ],
        ),
        _ => const Center(child: CircularProgressIndicator()),
      },
    );
  }
}

class _NasiyaCard extends ConsumerWidget {
  const _NasiyaCard(this.debt, {required this.run});

  final Debt debt;
  final Future<void> Function(
    BuildContext,
    WidgetRef,
    Future<void> Function(ObligationService),
  )
  run;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final closed = debt.remaining.isZero;
    return Card(
      key: Key('nasiya-${debt.meta.id}'),
      child: ListTile(
        title: Text(debt.creditorName),
        subtitle: Text(
          [
            if (closed)
              l10n.nasiyaPaid
            else
              l10n.nasiyaRemaining(context.money(debt.remaining)),
            if (debt.dueDate != null && !closed)
              l10n.nasiyaDue(formatDate(debt.dueDate!)),
          ].join(' · '),
        ),
        trailing: closed
            ? IconButton(
                tooltip: l10n.delete,
                icon: const Icon(Icons.delete_outline),
                onPressed: () =>
                    run(context, ref, (s) => s.deleteNasiya(debt.meta.id)),
              )
            : TextButton(
                key: Key('nasiya-pay-${debt.meta.id}'),
                onPressed: () async {
                  final m = await showAmountSheet(
                    context,
                    currency: debt.remaining.currency,
                    title: l10n.nasiyaPay,
                    initial: debt.remaining,
                    max: debt.remaining,
                  );
                  if (m == null || !context.mounted) return;
                  await run(context, ref, (s) => s.payNasiya(debt, m));
                },
                child: Text(l10n.nasiyaPay),
              ),
      ),
    );
  }
}

class _NasiyaForm extends ConsumerStatefulWidget {
  const _NasiyaForm();

  @override
  ConsumerState<_NasiyaForm> createState() => _NasiyaFormState();
}

class _NasiyaFormState extends ConsumerState<_NasiyaForm> {
  final _name = TextEditingController();
  Money? _amount;
  LocalDate? _due;

  @override
  void initState() {
    super.initState();
    // To'lash niyati (SPEC 2D.5): muddat majburiy — 30 kun keyinga.
    _due = Tashkent.dateOf(ref.read(clockProvider).nowUtc()).plusDays(30);
  }

  bool _busy = false;

  @override
  void dispose() {
    _name.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final valid =
        _name.text.trim().isNotEmpty && (_amount?.isPositive ?? false);
    return Padding(
      padding: EdgeInsets.fromLTRB(
        16,
        0,
        16,
        16 + MediaQuery.viewInsetsOf(context).bottom,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(l10n.nasiyaAdd, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 12),
          TextField(
            key: const Key('nasiya-name'),
            controller: _name,
            decoration: InputDecoration(
              labelText: l10n.nasiyaShopLabel,
              border: const OutlineInputBorder(),
            ),
            onChanged: (_) => setState(() {}),
          ),
          const SizedBox(height: 12),
          OutlinedButton(
            key: const Key('nasiya-amount'),
            onPressed: () async {
              final m = await showAmountSheet(
                context,
                currency: CurrencyCode.uzs,
                initial: _amount,
              );
              if (m != null) setState(() => _amount = m);
            },
            child: Text(
              _amount == null
                  ? l10n.nasiyaAmountLabel
                  : context.money(_amount!),
            ),
          ),
          const SizedBox(height: 8),
          OutlinedButton(
            key: const Key('nasiya-due'),
            onPressed: () async {
              final today = Tashkent.dateOf(ref.read(clockProvider).nowUtc());
              final picked = await showDatePicker(
                context: context,
                firstDate: DateTime(today.year - 1),
                lastDate: DateTime(today.year + 5),
                initialDate: DateTime(today.year, today.month, today.day),
              );
              if (picked != null) {
                setState(() => _due = LocalDate.fromDateTime(picked));
              }
            },
            child: Text(
              _due == null ? l10n.nasiyaDueLabel : formatDate(_due!),
            ),
          ),
          const SizedBox(height: 12),
          FilledButton(
            key: const Key('nasiya-save'),
            onPressed: valid && !_busy
                ? () async {
                    setState(() => _busy = true);
                    final navigator = Navigator.of(context);
                    try {
                      await (await ref.read(
                        obligationServiceProvider.future,
                      )).addNasiya(
                        shopName: _name.text,
                        amount: _amount!,
                        dueDate: _due!,
                      );
                      navigator.pop(true);
                    } on Object {
                      AppLog.event('nasiya_save_failed');
                      if (mounted) setState(() => _busy = false);
                    }
                  }
                : null,
            child: Text(l10n.save),
          ),
        ],
      ),
    );
  }
}
