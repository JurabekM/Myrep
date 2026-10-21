import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../core/query.dart';
import '../../shared/format.dart';
import '../../shared/widgets.dart';

const _results = ['OK', 'ADJUSTED', 'FAULTY'];

String? _opt(String v) => v.trim().isEmpty ? null : v.trim();

/// «Tarozingni to'g'ri tut» (kasbkor/SPEC 8.1, 8.4): oylik tarozi tekshiruvi (ilova o'lchamaydi —
/// odatni eslatadi va qayd etadi) va yillik inventarizatsiya (sanalgan miqdorlar bitta yozuvda).
class KkMeasureScreen extends ConsumerWidget {
  const KkMeasureScreen({required this.spaceId, super.key});

  final String spaceId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final id = spaceId;
    final settings = ref.watch(query(['kkGrowthSettings', id], (c) => c.kkGrowthSettings(spaceId: id))).valueOrNull;
    return ScreenBody(
      mentorKey: 'mentor.kkMeasure',
      children: [
        Hint(context.t('kk.measure.intro')),
        if (settings != null) _Scale(spaceId: id, s: settings),
        _Inventory(spaceId: id),
      ],
    );
  }
}

class _Scale extends ConsumerStatefulWidget {
  const _Scale({required this.spaceId, required this.s});

  final String spaceId;
  final KkGrowthSettingsDto s;

  @override
  ConsumerState<_Scale> createState() => _ScaleState();
}

class _ScaleState extends ConsumerState<_Scale> with ActionState {
  String _result = 'OK';
  final _note = TextEditingController();

  @override
  void dispose() {
    _note.dispose();
    super.dispose();
  }

  Future<void> _check() async {
    final r = await act(
      () => ref
          .read(coreProvider)
          .kkScaleCheck(
            spaceId: widget.spaceId,
            input: KkScaleCheckInput(result: _result, note: _opt(_note.text)),
          ),
    );
    if (r != null) _note.clear();
  }

  Future<void> _reminder(bool on) {
    final s = widget.s;
    return act(
      () => ref
          .read(coreProvider)
          .kkSetGrowthSettings(
            spaceId: widget.spaceId,
            input: KkGrowthSettingsInput(
              reserveMonths: s.reserveMonths,
              maxBadPercent: s.maxBadPercent,
              zakatMonth: s.zakatMonth,
              zakatDay: s.zakatDay,
              goldPrice: s.goldPrice?.plain,
              nisabGrams: s.nisabGrams,
              stockValuation: s.stockValuation,
              scaleReminder: on,
            ),
          ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final id = widget.spaceId;
    final pal = context.palette;
    final sc = ref.watch(query(['kkScale', id], (c) => c.kkScale(spaceId: id))).valueOrNull;
    return SectionCard(
      title: context.t('kk.measure.scale'),
      children: [
        CheckboxListTile(
          contentPadding: EdgeInsets.zero,
          controlAffinity: ListTileControlAffinity.leading,
          value: widget.s.scaleReminder,
          title: Text(context.t('kk.measure.reminder')),
          onChanged: busy ? null : (v) => _reminder(v ?? false),
        ),
        if (sc?.due ?? false)
          Text(
            context.t('kk.measure.due'),
            key: const Key('kk-scale-due'),
            style: TextStyle(color: pal.warn),
          ),
        const SizedBox(height: 8),
        Semantics(
          container: true,
          label: context.t('kk.measure.checkTitle'),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              SegmentedChoice<String>(
                label: context.t('kk.measure.result'),
                options: [for (final r in _results) (r, context.t('kk.measure.res.$r'))],
                value: _result,
                onChanged: (v) => setState(() => _result = v),
              ),
              const SizedBox(height: 12),
              Field(label: context.t('kk.measure.note'), controller: _note),
              ErrorText(error),
              const SizedBox(height: 8),
              Align(
                alignment: Alignment.centerLeft,
                child: FilledButton(onPressed: busy ? null : _check, child: Text(context.t('kk.measure.checkSave'))),
              ),
            ],
          ),
        ),
        if (sc != null && sc.checks.isNotEmpty) ...[
          const Divider(height: 24),
          for (final c in sc.checks.take(6))
            Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Text.rich(
                TextSpan(
                  children: [
                    TextSpan(text: '${showDate(c.checkedOn)} — ${context.t('kk.measure.res.${c.result}')}'),
                    if (c.note != null)
                      TextSpan(
                        text: ' · ${c.note}',
                        style: TextStyle(color: pal.inkMuted),
                      ),
                  ],
                ),
              ),
            ),
        ],
      ],
    );
  }
}

class _Inventory extends ConsumerStatefulWidget {
  const _Inventory({required this.spaceId});

  final String spaceId;

  @override
  ConsumerState<_Inventory> createState() => _InventoryState();
}

class _InventoryState extends ConsumerState<_Inventory> with ActionState {
  final _counted = <String, TextEditingController>{};
  final _reason = TextEditingController();

  @override
  void dispose() {
    for (final c in [..._counted.values, _reason]) {
      c.dispose();
    }
    super.dispose();
  }

  TextEditingController _ctl(String id) => _counted.putIfAbsent(id, TextEditingController.new);

  Future<void> _save(List<KkItemDto> items) async {
    final r = await act(
      () => ref
          .read(coreProvider)
          .kkInventory(
            spaceId: widget.spaceId,
            input: KkInventoryInput(
              reason: _reason.text,
              lines: [for (final i in items) KkInventoryLineInput(itemId: i.id, counted: _counted[i.id]?.text ?? '')],
            ),
          ),
    );
    if (r != null) {
      for (final c in _counted.values) {
        c.clear();
      }
      _reason.clear();
    }
  }

  @override
  Widget build(BuildContext context) {
    final id = widget.spaceId;
    final pal = context.palette;
    final items = ref.watch(query(['kkStock', id], (c) => c.kkStock(spaceId: id))).valueOrNull?.items ?? const [];
    final counts = ref.watch(query(['kkStockCounts', id], (c) => c.kkStockCounts(spaceId: id))).valueOrNull ?? const [];
    return SectionCard(
      title: context.t('kk.measure.inventory'),
      children: [
        Hint(context.t('kk.measure.inventoryHint')),
        if (items.isEmpty) ...[const SizedBox(height: 8), Hint(context.t('kk.stock.empty'))],
        if (items.isNotEmpty)
          Semantics(
            container: true,
            label: context.t('kk.measure.inventoryForm'),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                for (final i in items)
                  Builder(
                    builder: (context) {
                      final unit = context.t('kk.unit.${i.unit}');
                      return Container(
                        padding: const EdgeInsets.symmetric(vertical: 8),
                        decoration: BoxDecoration(
                          border: Border(top: BorderSide(color: pal.line)),
                        ),
                        child: Row(
                          children: [
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(i.name, style: const TextStyle(fontWeight: FontWeight.w600)),
                                  Hint('${context.t('kk.measure.book')}: ${i.qty} $unit'),
                                ],
                              ),
                            ),
                            const SizedBox(width: 12),
                            SizedBox(
                              width: 140,
                              child: Semantics(
                                label: context.t('kk.measure.countedNamed', {'name': i.name, 'unit': unit}),
                                child: Field(
                                  label: context.t('kk.measure.counted'),
                                  controller: _ctl(i.id),
                                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                                ),
                              ),
                            ),
                          ],
                        ),
                      );
                    },
                  ),
                const SizedBox(height: 8),
                Field(label: context.t('kk.measure.reason'), controller: _reason),
                ErrorText(error),
                const SizedBox(height: 8),
                Align(
                  alignment: Alignment.centerLeft,
                  child: FilledButton(
                    onPressed: busy ? null : () => _save(items),
                    child: Text(context.t('kk.measure.inventorySave')),
                  ),
                ),
              ],
            ),
          ),
        if (counts.isNotEmpty) ...[
          const Divider(height: 24),
          for (final c in counts)
            Padding(
              key: ValueKey(('kk-count-row', c)),
              padding: const EdgeInsets.only(bottom: 4),
              child: Text(
                context.t('kk.measure.countLine', {
                  'date': showDate(c.countedOn),
                  'counted': c.counted,
                  'changed': c.changed,
                  'before': c.valueBefore.formatted,
                  'after': c.valueAfter.formatted,
                }),
              ),
            ),
        ],
      ],
    );
  }
}
