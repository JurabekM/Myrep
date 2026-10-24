import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/refresh.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/app/widgets/paged_list.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/features/budget/presentation/havas_screen.dart';
import 'package:baraka_daftari/features/content/data/content_providers.dart';
import 'package:baraka_daftari/features/content/domain/content.dart';
import 'package:baraka_daftari/features/prices/data/price_providers.dart';
import 'package:baraka_daftari/features/prices/domain/price_book_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Ishorali foiz: 6250 → «+62,5 %», −2000 → «−20 %».
String signedPercent(int bp) =>
    '${bp < 0 ? '−' : '+'}${percentLabel(bp.abs())} %';

/// «1,5» / «4» → mingdan birlar (1500 / 4000); noto'g'ri — `null`.
int? parseMilli(String text) {
  final m = RegExp(r'^(\d{1,6})(?:[.,](\d{1,3}))?$').firstMatch(text.trim());
  if (m == null) return null;
  final frac = (m[2] ?? '').padRight(3, '0');
  final v = int.parse(m[1]!) * 1000 + int.parse(frac);
  return v > 0 ? v : null;
}

/// «Narx daftari» (SPEC 2C.1): savat, narx tarixi, shaxsiy inflyatsiya.
class PricesScreen extends ConsumerWidget {
  const PricesScreen({super.key});

  Future<void> _addItem(BuildContext context, WidgetRef ref) async {
    final draft = await showDialog<(String, String, int)>(
      context: context,
      builder: (_) => const _ItemDialog(),
    );
    if (draft == null) return;
    try {
      await (await ref.read(priceBookServiceProvider.future)).addItem(
        name: draft.$1,
        unit: draft.$2,
        monthlyQuantityMilli: draft.$3,
      );
      ref.invalidate(priceBookProvider);
      if (context.mounted) await syncTreatReminders(ref, context.l10n);
    } on Object {
      AppLog.event('price_item_failed');
    }
  }

  Future<void> _addPrice(
    BuildContext context,
    WidgetRef ref,
    ItemHistory h,
  ) async {
    final l10n = context.l10n;
    final messenger = ScaffoldMessenger.of(context);
    final price = await showAmountSheet(
      context,
      currency: CurrencyCode.uzs,
      title: l10n.priceAddTitle(h.item.name, h.item.unit),
      initial: h.last?.price,
    );
    if (price == null || !price.isPositive) return;
    try {
      await (await ref.read(
        priceBookServiceProvider.future,
      )).addPrice(h.item, price);
      ref.invalidate(priceBookProvider);
      refreshMoneyViews(ref);
      await recordTaskEvent(ref, TaskTrigger.priceComparisonDone);
      messenger.showSnackBar(SnackBar(content: Text(l10n.priceSaved)));
    } on Object {
      AppLog.event('price_add_failed');
      messenger.showSnackBar(SnackBar(content: Text(l10n.genericError)));
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final money = context.money;
    final book = ref.watch(priceBookProvider);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.pricesTitle)),
      floatingActionButton: FloatingActionButton.extended(
        key: const Key('price-item-add'),
        icon: const Icon(Icons.add),
        label: Text(l10n.priceItemAdd),
        onPressed: () => _addItem(context, ref),
      ),
      body: switch (book) {
        AsyncData(:final value) => ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 96),
          children: [
            Text(l10n.pricesHint),
            const SizedBox(height: 8),
            Card(
              key: const Key('inflation-card'),
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (value.yearInflationBp == null &&
                        value.sinceStartBp == null)
                      Text(l10n.inflationUnknown)
                    else ...[
                      if (value.yearInflationBp != null)
                        Text(
                          l10n.inflationYear(
                            signedPercent(value.yearInflationBp!),
                          ),
                          key: const Key('inflation-year'),
                          style: theme.textTheme.titleMedium,
                        ),
                      if (value.sinceStartBp != null)
                        Text(
                          l10n.inflationSince(
                            formatDate(value.startDate!),
                            signedPercent(value.sinceStartBp!),
                          ),
                          key: const Key('inflation-since'),
                        ),
                    ],
                    if (value.streakWeeks > 0)
                      Text(
                        l10n.priceStreak(value.streakWeeks),
                        style: theme.textTheme.bodySmall,
                      ),
                  ],
                ),
              ),
            ),
            if (value.items.isEmpty)
              Padding(
                padding: const EdgeInsets.all(24),
                child: Text(l10n.pricesEmpty, textAlign: TextAlign.center),
              ),
            PagedList(
              count: value.items.length,
              itemBuilder: (context, i) {
                final h = value.items[i];
                return Card(
                  key: Key('price-item-${h.item.meta.id}'),
                  child: ExpansionTile(
                    title: Text('${h.item.name} (1 ${h.item.unit})'),
                    subtitle: Text(
                      [
                        if (h.last != null)
                          l10n.priceLast(
                            money(h.last!.price),
                            formatDate(h.last!.observedOn),
                          ),
                        if (h.changeBp != null)
                          l10n.priceChange(
                            formatDate(h.first!.observedOn),
                            money(h.first!.price),
                            money(h.last!.price),
                            signedPercent(h.changeBp!),
                          ),
                      ].join('\n'),
                    ),
                    trailing: IconButton(
                      key: Key('price-add-${h.item.meta.id}'),
                      tooltip: l10n.priceAdd,
                      icon: const Icon(Icons.edit_note),
                      onPressed: () => _addPrice(context, ref, h),
                    ),
                    children: [
                      for (final p in h.points.reversed)
                        ListTile(
                          dense: true,
                          title: Text(money(p.price)),
                          subtitle: Text(
                            [
                              formatDate(p.observedOn),
                              if (p.place != null) p.place!,
                            ].join(' · '),
                          ),
                        ),
                    ],
                  ),
                );
              },
            ),
          ],
        ),
        AsyncError() => Center(child: Text(l10n.genericError)),
        _ => const Center(child: CircularProgressIndicator()),
      },
    );
  }
}

class _ItemDialog extends StatefulWidget {
  const _ItemDialog();

  @override
  State<_ItemDialog> createState() => _ItemDialogState();
}

class _ItemDialogState extends State<_ItemDialog> {
  final _name = TextEditingController();
  final _unit = TextEditingController(text: 'kg');
  final _qty = TextEditingController(text: '1');

  @override
  void dispose() {
    _name.dispose();
    _unit.dispose();
    _qty.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final qty = parseMilli(_qty.text);
    final valid =
        _name.text.trim().isNotEmpty &&
        _unit.text.trim().isNotEmpty &&
        qty != null;
    return AlertDialog(
      title: Text(l10n.priceItemAdd),
      scrollable: true,
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          TextField(
            key: const Key('price-item-name'),
            controller: _name,
            autofocus: true,
            decoration: InputDecoration(labelText: l10n.titleLabel),
            onChanged: (_) => setState(() {}),
          ),
          TextField(
            key: const Key('price-item-unit'),
            controller: _unit,
            decoration: InputDecoration(labelText: l10n.priceUnitLabel),
            onChanged: (_) => setState(() {}),
          ),
          TextField(
            key: const Key('price-item-qty'),
            controller: _qty,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            inputFormatters: [
              FilteringTextInputFormatter.allow(RegExp('[0-9.,]')),
            ],
            decoration: InputDecoration(labelText: l10n.priceQuantityLabel),
            onChanged: (_) => setState(() {}),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text(l10n.cancel),
        ),
        FilledButton(
          key: const Key('price-item-save'),
          onPressed: valid
              ? () => Navigator.pop(context, (
                  _name.text.trim(),
                  _unit.text.trim(),
                  qty,
                ))
              : null,
          child: Text(l10n.save),
        ),
      ],
    );
  }
}
