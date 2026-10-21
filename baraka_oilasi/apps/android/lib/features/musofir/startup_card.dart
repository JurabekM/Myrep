import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/shell_state.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../core/query.dart';
import '../../shared/widgets.dart';

/// Qaytgandan keyingi ish (musofir/SPEC 6.2, 6.6): ish boshlash summasi — qaytish jamg'armasi
/// maqsadining bir qismi; Uy makonidagi «Hunardan ishga» g'oyasiga bog'lanadi. Bo'linish (yashash
/// uchun) — yadrodan.
class StartupCard extends ConsumerStatefulWidget {
  const StartupCard({required this.spaceId, required this.d, required this.homeCurrency, super.key});

  final String spaceId;
  final MfOverviewDto d;
  final String homeCurrency;

  @override
  ConsumerState<StartupCard> createState() => _StartupCardState();
}

class _StartupCardState extends ConsumerState<StartupCard> {
  bool _editing = false;

  void _openIdeas(String uyId) {
    ref.read(shellProvider.notifier)
      ..setSpace(uyId)
      ..go('ideas');
  }

  @override
  Widget build(BuildContext context) {
    final spaces = ref.watch(query(['household'], (c) => c.household())).valueOrNull?.spaces ?? const [];
    final uyId = spaces.where((s) => s.kind == 'UY').firstOrNull?.id;
    final s = widget.d.startup;
    final pal = context.palette;
    return SectionCard(
      title: context.t('mf.startup.title'),
      children: [
        if (_editing && uyId != null)
          _StartupForm(
            spaceId: widget.spaceId,
            uyId: uyId,
            d: widget.d,
            homeCurrency: widget.homeCurrency,
            onDone: () => setState(() => _editing = false),
          )
        else if (s != null)
          Column(
            key: const Key('mf-startup'),
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                [
                  context.t('mf.startup.amountLine', {'amount': s.startup.formatted}),
                  ?s.ideaTitle,
                ].join(' · '),
              ),
              if (s.living != null)
                Hint(
                  context.t('mf.startup.livingLine', {'amount': s.living!.formatted, 'percent': s.startupPercent}),
                ),
              if (s.exceedsTarget) Text(context.t('mf.startup.exceeds'), style: TextStyle(color: pal.warn)),
            ],
          )
        else
          Hint(context.t('mf.startup.intro')),
        if (!_editing) ...[
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              if (uyId != null)
                OutlinedButton(
                  onPressed: () => setState(() => _editing = true),
                  child: Text(context.t(s != null ? 'mf.startup.change' : 'mf.startup.set')),
                ),
              OutlinedButton(
                onPressed: uyId == null ? null : () => _openIdeas(uyId),
                child: Text(context.t('mf.startup.openIdeas')),
              ),
            ],
          ),
        ],
      ],
    );
  }
}

class _StartupForm extends ConsumerStatefulWidget {
  const _StartupForm({
    required this.spaceId,
    required this.uyId,
    required this.d,
    required this.homeCurrency,
    required this.onDone,
  });

  final String spaceId;
  final String uyId;
  final MfOverviewDto d;
  final String homeCurrency;
  final VoidCallback onDone;

  @override
  ConsumerState<_StartupForm> createState() => _StartupFormState();
}

class _StartupFormState extends ConsumerState<_StartupForm> with ActionState {
  late String _ideaId = widget.d.startup?.ideaId ?? '';
  late final _amount = TextEditingController(text: widget.d.startup?.startup.plain);

  @override
  void dispose() {
    _amount.dispose();
    super.dispose();
  }

  Future<void> _save({required bool clear}) async {
    final r = await act(
      () => ref
          .read(coreProvider)
          .mfSetPlan(
            spaceId: widget.spaceId,
            input: MfPlanInput(
              reserveMonths: widget.d.reserve?.months,
              startup: clear || _amount.text.trim().isEmpty ? null : _amount.text.trim(),
              startupIdeaId: clear || _ideaId.isEmpty ? null : _ideaId,
            ),
          ),
    );
    if (r != null) widget.onDone();
  }

  @override
  Widget build(BuildContext context) {
    final uy = widget.uyId;
    final ideas = ref.watch(query(['ideas', uy], (c) => c.ventureIdeas(spaceId: uy))).valueOrNull ?? const [];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Select<String>(
          label: context.t('mf.startup.idea'),
          items: [
            ('', context.t('mf.startup.noIdea')),
            for (final i in ideas) (i.id, '${i.title} · ${i.capex.formatted}'),
          ],
          value: _ideaId,
          onChanged: (v) => setState(() {
            _ideaId = v ?? '';
            // G'oyaning boshlang'ich sarmoyasi — taklif (uy valyutasida bo'lsa).
            final capex = ideas.where((i) => i.id == _ideaId).firstOrNull?.capex;
            if (capex != null && capex.currency == widget.homeCurrency) _amount.text = capex.plain;
          }),
        ),
        const SizedBox(height: 12),
        AmountField(
          label: context.t('mf.startup.amount', {'currency': widget.homeCurrency}),
          controller: _amount,
        ),
        Hint(context.t('mf.startup.hint')),
        ErrorText(error),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            FilledButton(
              onPressed: busy ? null : () => _save(clear: false),
              child: Text(context.t('common.save')),
            ),
            if (widget.d.startup != null)
              OutlinedButton(
                onPressed: busy ? null : () => _save(clear: true),
                child: Text(context.t('mf.startup.remove')),
              ),
            TextButton(onPressed: widget.onDone, child: Text(context.t('common.cancel'))),
          ],
        ),
      ],
    );
  }
}
