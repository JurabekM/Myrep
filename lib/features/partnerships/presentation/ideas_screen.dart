import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/app/widgets/text_prompt.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/money/allocation.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/features/content/data/content_providers.dart';
import 'package:baraka_daftari/features/content/domain/content.dart';
import 'package:baraka_daftari/features/partnerships/data/partnership_providers.dart';
import 'package:baraka_daftari/features/partnerships/domain/idea_math.dart';
import 'package:baraka_daftari/features/partnerships/domain/partnership_rules.dart';
import 'package:baraka_daftari/features/partnerships/domain/venture_service.dart';
import 'package:baraka_daftari/features/partnerships/presentation/partnership_wizard_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

String scenarioLabel(BuildContext context, IdeaScenario s) {
  final l10n = context.l10n;
  return switch (s) {
    IdeaScenario.pessimistic => l10n.scenarioPessimistic,
    IdeaScenario.base => l10n.scenarioBase,
    IdeaScenario.optimistic => l10n.scenarioOptimistic,
  };
}

/// Uch stsenariy jadvali (SPEC 2E.4).
class ScenarioTable extends StatelessWidget {
  const ScenarioTable({required this.results, this.shared = false, super.key});

  final List<IdeaScenarioResult> results;
  final bool shared;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final money = context.money;
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (final r in results)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Column(
              key: Key('idea-scenario-${r.scenario.name}'),
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  scenarioLabel(context, r.scenario),
                  style: theme.textTheme.titleSmall,
                ),
                Text(
                  l10n.ideaScenarioLine(
                    money(r.income),
                    money(r.expense),
                    money(r.net),
                  ),
                  style: theme.textTheme.bodySmall,
                ),
                if (shared) Text(l10n.ideaMyNet(money(r.myNet))),
                Text(
                  r.paybackMonths == null
                      ? l10n.ideaNoPayback
                      : l10n.ideaPayback(r.paybackMonths!),
                  key: Key('idea-payback-${r.scenario.name}'),
                  style: TextStyle(
                    color: r.paybackMonths == null
                        ? theme.colorScheme.error
                        : theme.colorScheme.primary,
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

/// «Hunardan ishga» (SPEC 2E.4): hunarlar va g'oyalar.
class IdeasScreen extends ConsumerWidget {
  const IdeasScreen({super.key});

  Future<void> _addSkill(BuildContext context, WidgetRef ref) async {
    final l10n = context.l10n;
    final name = await showTextPrompt(
      context,
      title: l10n.skillAdd,
      label: l10n.skillName,
      fieldKey: const Key('skill-name'),
      okKey: const Key('skill-ok'),
    );
    if (name == null || name.trim().isEmpty) return;
    await (await ref.read(ideaServiceProvider.future)).addSkill(name);
    ref.invalidate(ideasOverviewProvider);
  }

  void _toContract(BuildContext context, IdeaView v) => context.push(
    AppRoutes.partnershipNew,
    extra: PartnershipPrefill(
      title: v.idea.title,
      capital: [
        for (final c in v.capex)
          CapitalItem(
            kind: CapitalKind.equipment,
            title: c.title,
            amount: c.amount,
          ),
      ],
    ),
  );

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final money = context.money;
    final data = ref.watch(ideasOverviewProvider);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.ideasTitle)),
      floatingActionButton: FloatingActionButton.extended(
        key: const Key('idea-add'),
        icon: const Icon(Icons.add),
        label: Text(l10n.ideaAdd),
        onPressed: () async {
          await context.push(AppRoutes.ideaNew);
          ref.invalidate(ideasOverviewProvider);
        },
      ),
      body: switch (data) {
        AsyncData(:final value) => ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 96),
          children: [
            Text(l10n.ideasHint),
            const SizedBox(height: 12),
            Text(l10n.skillsTitle, style: theme.textTheme.titleSmall),
            Wrap(
              spacing: 8,
              runSpacing: 4,
              children: [
                for (final s in value.$1)
                  InputChip(
                    label: Text(s.name),
                    onDeleted: () async {
                      await (await ref.read(
                        ideaServiceProvider.future,
                      )).removeSkill(s);
                      ref.invalidate(ideasOverviewProvider);
                    },
                  ),
                ActionChip(
                  key: const Key('skill-add'),
                  avatar: const Icon(Icons.add, size: 18),
                  label: Text(l10n.skillAdd),
                  onPressed: () => _addSkill(context, ref),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(l10n.ideasList, style: theme.textTheme.titleSmall),
            for (final v in value.$2)
              Card(
                key: Key('idea-${v.idea.meta.id}'),
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 12, 8, 8),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(v.idea.title, style: theme.textTheme.titleMedium),
                      Text(l10n.ideaCapexTotal(money(v.capexTotal))),
                      ScenarioTable(
                        results: v.scenarios,
                        shared: v.idea.myShareBp < basisPointsWhole,
                      ),
                      Align(
                        alignment: Alignment.centerRight,
                        child: TextButton.icon(
                          key: Key('idea-contract-${v.idea.meta.id}'),
                          icon: const Icon(Icons.description_outlined),
                          label: Text(l10n.ideaToContract),
                          onPressed: () => _toContract(context, v),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
          ],
        ),
        AsyncError() => Center(child: Text(l10n.genericError)),
        _ => const Center(child: CircularProgressIndicator()),
      },
    );
  }
}

/// G'oya hisobi: CAPEX, oylik kirim va xarajat, ulush — uch stsenariy
/// jonli ko'rinadi.
class IdeaNewScreen extends ConsumerStatefulWidget {
  const IdeaNewScreen({super.key});

  @override
  ConsumerState<IdeaNewScreen> createState() => _IdeaNewScreenState();
}

class _IdeaNewScreenState extends ConsumerState<IdeaNewScreen> {
  final _title = TextEditingController();
  final _share = TextEditingController(text: '100');
  final List<(String, Money)> _capex = [];
  Money _income = const Money.zero(CurrencyCode.uzs);
  Money _expense = const Money.zero(CurrencyCode.uzs);
  String? _skillId;
  bool _saving = false;

  /// Hunar shabloni (SPEC 2G.8): CAPEX tavsiyalari va talab savoli.
  bool _workshop = false;

  @override
  void dispose() {
    _title.dispose();
    _share.dispose();
    super.dispose();
  }

  int get _shareBp => parsePercentBp(_share.text) ?? basisPointsWhole;

  Money get _capexTotal => Money.sum(_capex.map((x) => x.$2), CurrencyCode.uzs);

  Future<void> _addCapex() async {
    final l10n = context.l10n;
    final title = await showTextPrompt(
      context,
      title: l10n.ideaCapexAdd,
      label: l10n.ideaCapexTitle,
      fieldKey: const Key('capex-title'),
      okKey: const Key('capex-ok'),
    );
    if (title == null || title.trim().isEmpty || !mounted) return;
    await _addCapexNamed(title.trim());
  }

  /// Shablondagi nom bilan — summani foydalanuvchi yozadi (narx o'ylab
  /// topilmaydi).
  Future<void> _addCapexNamed(String title) async {
    final amount = await showAmountSheet(
      context,
      currency: CurrencyCode.uzs,
      title: title,
    );
    if (amount == null || !amount.isPositive || !mounted) return;
    setState(() => _capex.add((title, amount)));
  }

  Future<void> _save() async {
    final navigator = Navigator.of(context);
    final messenger = ScaffoldMessenger.of(context);
    final errorText = context.l10n.genericError;
    setState(() => _saving = true);
    try {
      await (await ref.read(ideaServiceProvider.future)).addIdea(
        title: _title.text,
        baseIncome: _income,
        monthlyExpense: _expense,
        capex: _capex,
        myShareBp: _shareBp,
        skillId: _skillId,
      );
      await recordTaskEvent(ref, TaskTrigger.ventureIdeaCreated);
      navigator.pop();
    } on Object {
      AppLog.event('idea_save_failed');
      messenger.showSnackBar(SnackBar(content: Text(errorText)));
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final money = context.money;
    final skills = ref.watch(ideasOverviewProvider).valueOrNull?.$1 ?? [];
    final (pess, opt) = defaultScenarioIncomes(_income);
    final results = [
      for (final (s, inc) in [
        (IdeaScenario.pessimistic, pess),
        (IdeaScenario.base, _income),
        (IdeaScenario.optimistic, opt),
      ])
        evaluateScenario(
          scenario: s,
          capex: _capexTotal,
          income: inc,
          expense: _expense,
          myShareBp: _shareBp,
        ),
    ];
    return Scaffold(
      appBar: AppBar(title: Text(l10n.ideaAdd)),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
        children: [
          TextField(
            key: const Key('idea-title'),
            controller: _title,
            decoration: InputDecoration(labelText: l10n.ideaName),
            onChanged: (_) => setState(() {}),
          ),
          if (skills.isNotEmpty) ...[
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: [
                for (final s in skills)
                  ChoiceChip(
                    label: Text(s.name),
                    selected: _skillId == s.meta.id,
                    onSelected: (on) =>
                        setState(() => _skillId = on ? s.meta.id : null),
                  ),
              ],
            ),
          ],
          const SizedBox(height: 12),
          // Chip bir qatorli — uzun shablon nomi qurilmada kesilardi;
          // tugma matni qatorga o'raladi.
          Align(
            alignment: Alignment.centerLeft,
            child: OutlinedButton.icon(
              key: const Key('idea-tpl-workshop'),
              icon: const Icon(Icons.build_outlined),
              label: Text(l10n.ideaTplWorkshop),
              onPressed: () => setState(() => _workshop = !_workshop),
            ),
          ),
          if (_workshop) ...[
            const SizedBox(height: 4),
            Text(l10n.ideaTplSuggest),
            Wrap(
              spacing: 8,
              runSpacing: 4,
              children: [
                for (final (i, name) in [
                  l10n.ideaTplWelder,
                  l10n.ideaTplGrinder,
                  l10n.ideaTplRent,
                  l10n.ideaTplMetal,
                  l10n.ideaTplSafety,
                ].indexed)
                  ActionChip(
                    key: Key('capex-suggest-$i'),
                    label: Text(name),
                    onPressed: _capex.any((c) => c.$1 == name)
                        ? null
                        : () => _addCapexNamed(name),
                  ),
              ],
            ),
            const SizedBox(height: 4),
            Text(l10n.ideaDemandQ, style: theme.textTheme.bodySmall),
          ],
          const SizedBox(height: 12),
          Text(l10n.ideaCapex, style: theme.textTheme.titleSmall),
          for (final (i, (t, a)) in _capex.indexed)
            ListTile(
              dense: true,
              contentPadding: EdgeInsets.zero,
              title: Text(t),
              subtitle: Text(money(a)),
              trailing: IconButton(
                icon: const Icon(Icons.close),
                onPressed: () => setState(() => _capex.removeAt(i)),
              ),
            ),
          Text(l10n.ideaCapexTotal(money(_capexTotal))),
          Align(
            alignment: Alignment.centerLeft,
            child: TextButton.icon(
              key: const Key('capex-add'),
              icon: const Icon(Icons.add),
              label: Text(l10n.ideaCapexAdd),
              onPressed: _addCapex,
            ),
          ),
          Wrap(
            spacing: 8,
            runSpacing: 4,
            children: [
              OutlinedButton(
                key: const Key('idea-income'),
                onPressed: () async {
                  final m = await showAmountSheet(
                    context,
                    currency: CurrencyCode.uzs,
                    title: l10n.ideaIncomeTitle,
                    initial: _income,
                  );
                  if (m != null) setState(() => _income = m);
                },
                child: Text(l10n.ideaIncome(money(_income))),
              ),
              OutlinedButton(
                key: const Key('idea-expense'),
                onPressed: () async {
                  final m = await showAmountSheet(
                    context,
                    currency: CurrencyCode.uzs,
                    title: l10n.ideaExpenseTitle,
                    initial: _expense,
                  );
                  if (m != null) setState(() => _expense = m);
                },
                child: Text(l10n.ideaExpense(money(_expense))),
              ),
            ],
          ),
          TextField(
            key: const Key('idea-share'),
            controller: _share,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: InputDecoration(labelText: l10n.ideaShare),
            onChanged: (_) => setState(() {}),
          ),
          const SizedBox(height: 8),
          ScenarioTable(
            results: results,
            shared: _shareBp < basisPointsWhole,
          ),
          const SizedBox(height: 16),
          FilledButton(
            key: const Key('idea-save'),
            onPressed: _saving || _title.text.trim().isEmpty ? null : _save,
            child: Text(l10n.ideaSave),
          ),
        ],
      ),
    );
  }
}
