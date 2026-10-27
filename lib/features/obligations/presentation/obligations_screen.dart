import 'dart:async';

import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/refresh.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/features/obligations/data/obligation_providers.dart';
import 'package:baraka_daftari/features/obligations/domain/obligation.dart';
import 'package:baraka_daftari/features/obligations/presentation/obligation_views.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Doimiy to'lovlar: ijara, kredit, kommunal (SPEC 2.5). To'lovdan 1 kun
/// oldin eslatma (Kotlin WorkManager).
class ObligationsScreen extends ConsumerStatefulWidget {
  const ObligationsScreen({super.key});

  @override
  ConsumerState<ObligationsScreen> createState() => _ObligationsScreenState();
}

class _ObligationsScreenState extends ConsumerState<ObligationsScreen> {
  bool? _notificationsOn;
  late final AppLifecycleListener _lifecycle;

  @override
  void initState() {
    super.initState();
    unawaited(_checkNotifications());
    // Tizim ruxsat oynasidan qaytgach holat qayta tekshiriladi (ruxsat so'rovi
    // javobni kutmaydi — qurilmada topilgan xato).
    _lifecycle = AppLifecycleListener(
      onResume: () => unawaited(_checkNotifications()),
    );
  }

  @override
  void dispose() {
    _lifecycle.dispose();
    super.dispose();
  }

  Future<void> _checkNotifications() async {
    try {
      final on = await ref.read(reminderApiProvider).areNotificationsEnabled();
      if (mounted) setState(() => _notificationsOn = on);
    } on Object {
      AppLog.event('notifications_check_failed');
    }
  }

  Future<void> _edit([Obligation? existing]) async {
    final l10n = context.l10n;
    final saved = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (_) => _ObligationForm(existing: existing),
    );
    if (saved != true || !mounted) return;
    refreshMoneyViews(ref);
    await syncObligationReminders(ref, l10n);
    if (_notificationsOn == false) {
      await ref.read(reminderApiProvider).requestNotificationPermission();
    }
    await _checkNotifications();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final list = ref.watch(obligationsListProvider);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.sectionObligations)),
      floatingActionButton: FloatingActionButton.extended(
        key: const Key('obligation-add'),
        icon: const Icon(Icons.add),
        label: Text(l10n.obligationAdd),
        onPressed: _edit,
      ),
      body: switch (list) {
        AsyncError() => Center(child: Text(l10n.genericError)),
        AsyncData(:final value) => ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 96),
          children: [
            if (_notificationsOn == false)
              Card(
                child: ListTile(
                  key: const Key('notifications-off'),
                  leading: const Icon(Icons.notifications_off_outlined),
                  title: Text(l10n.notificationsOff),
                  trailing: TextButton(
                    onPressed: () async {
                      await ref
                          .read(reminderApiProvider)
                          .requestNotificationPermission();
                      await _checkNotifications();
                    },
                    child: Text(l10n.notificationsEnable),
                  ),
                ),
              ),
            if (value.isEmpty)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 24),
                child: Text(l10n.obligationsEmpty, textAlign: TextAlign.center),
              )
            else ...[
              Text(
                l10n.obligationsMonthly(
                  context.money(
                    Money.sum(
                      value.map((o) => o.amount),
                      value.first.amount.currency,
                    ),
                  ),
                ),
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 8),
              Card(
                child: Column(
                  children: [
                    for (final (i, o) in value.indexed) ...[
                      if (i > 0) const Divider(height: 1),
                      ListTile(
                        key: Key('obligation-${o.meta.id}'),
                        title: Text(o.title),
                        subtitle: Text(
                          '${l10n.obligationKind(o.kind)} · '
                          '${l10n.obligationDay(o.dayOfMonth)}',
                        ),
                        trailing: Text(context.money(o.amount)),
                        onTap: () => _edit(o),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ],
        ),
        _ => const Center(child: CircularProgressIndicator()),
      },
    );
  }
}

class _ObligationForm extends ConsumerStatefulWidget {
  const _ObligationForm({this.existing});

  final Obligation? existing;

  @override
  ConsumerState<_ObligationForm> createState() => _ObligationFormState();
}

class _ObligationFormState extends ConsumerState<_ObligationForm> {
  late final _title = TextEditingController(text: widget.existing?.title);
  late ObligationKind _kind = widget.existing?.kind ?? ObligationKind.rent;
  late int _day = widget.existing?.dayOfMonth ?? 1;
  late Money? _amount = widget.existing?.amount;
  bool _busy = false;

  @override
  void dispose() {
    _title.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    setState(() => _busy = true);
    final navigator = Navigator.of(context);
    final messenger = ScaffoldMessenger.of(context);
    final error = context.l10n.genericError;
    try {
      final service = await ref.read(obligationServiceProvider.future);
      final e = widget.existing;
      if (e == null) {
        await service.addObligation(
          title: _title.text,
          kind: _kind,
          amount: _amount!,
          dayOfMonth: _day,
        );
      } else {
        await service.updateObligation(
          e.copyWith(
            title: _title.text,
            kind: _kind,
            amount: _amount!,
            dayOfMonth: _day,
          ),
        );
      }
      navigator.pop(true);
    } on Object {
      AppLog.event('obligation_save_failed');
      messenger.showSnackBar(SnackBar(content: Text(error)));
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _delete() async {
    final navigator = Navigator.of(context);
    await (await ref.read(
      obligationServiceProvider.future,
    )).deleteObligation(widget.existing!.meta.id);
    navigator.pop(true);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final valid =
        _title.text.trim().isNotEmpty && (_amount?.isPositive ?? false);
    return Padding(
      padding: EdgeInsets.fromLTRB(
        16,
        0,
        16,
        16 + MediaQuery.viewInsetsOf(context).bottom,
      ),
      child: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              widget.existing == null
                  ? l10n.obligationAdd
                  : l10n.obligationEdit,
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 12),
            TextField(
              key: const Key('obligation-title'),
              controller: _title,
              decoration: InputDecoration(
                labelText: l10n.obligationTitleLabel,
                border: const OutlineInputBorder(),
              ),
              onChanged: (_) => setState(() {}),
            ),
            const SizedBox(height: 12),
            Text(l10n.obligationKindLabel),
            Wrap(
              spacing: 8,
              children: [
                for (final k in ObligationKind.values)
                  ChoiceChip(
                    key: Key('kind-${k.name}'),
                    label: Text(l10n.obligationKind(k)),
                    selected: k == _kind,
                    onSelected: (_) => setState(() => _kind = k),
                  ),
              ],
            ),
            const SizedBox(height: 12),
            OutlinedButton(
              key: const Key('obligation-amount'),
              onPressed: () async {
                final m = await showAmountSheet(
                  context,
                  currency: _amount?.currency ?? CurrencyCode.uzs,
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
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(child: Text(l10n.obligationDayLabel)),
                DropdownButton<int>(
                  key: const Key('obligation-day'),
                  value: _day,
                  items: [
                    for (var d = 1; d <= 31; d++)
                      DropdownMenuItem(value: d, child: Text('$d')),
                  ],
                  onChanged: (d) => setState(() => _day = d ?? _day),
                ),
              ],
            ),
            const SizedBox(height: 12),
            FilledButton(
              key: const Key('obligation-save'),
              onPressed: valid && !_busy ? _save : null,
              child: Text(l10n.save),
            ),
            if (widget.existing != null)
              TextButton(
                key: const Key('obligation-delete'),
                onPressed: _busy ? null : _delete,
                child: Text(l10n.delete),
              ),
          ],
        ),
      ),
    );
  }
}
