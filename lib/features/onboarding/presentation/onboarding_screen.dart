import 'dart:async';

import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/refresh.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/app/settings/app_settings.dart';
import 'package:baraka_daftari/app/settings/settings_controller.dart';
import 'package:baraka_daftari/app/widgets/brand_logo.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/household/data/household_providers.dart';
import 'package:baraka_daftari/features/household/presentation/member_views.dart';
import 'package:baraka_daftari/features/onboarding/data/onboarding_providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// Onboarding (MVP_PLAN Vazifa 15): PIN (oldingi ekran) + 4 qadam — til,
/// oila a'zolari, daromad turi, faol qarz. Jami 5 ekran.
class OnboardingScreen extends ConsumerStatefulWidget {
  const OnboardingScreen({super.key});

  /// PIN o'rnatish birinchi ekran hisoblanadi.
  static const totalSteps = 5;

  @override
  ConsumerState<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends ConsumerState<OnboardingScreen> {
  var _step = 0;
  var _busy = false;
  IncomeKind? _kind;
  var _salaryDay = 1;
  bool? _hasDebt;
  final _owner = TextEditingController();
  final _member = TextEditingController();
  var _memberChild = false;

  @override
  void dispose() {
    _owner.dispose();
    _member.dispose();
    super.dispose();
  }

  bool get _canNext => switch (_step) {
    2 => _kind != null,
    3 => _hasDebt != null,
    _ => true,
  };

  Future<void> _saveOwner() async {
    final l10n = context.l10n;
    final service = await ref.read(householdServiceProvider.future);
    final members = await service.members(ownerName: '');
    final owner = members.firstWhere((m) => m.isOwner);
    final name = _owner.text.trim();
    if (name.isNotEmpty && name != owner.displayName) {
      await service.rename(owner, name);
    } else if (name.isEmpty && owner.displayName.isEmpty) {
      await service.rename(owner, l10n.memberOwnerDefault);
    }
    ref.invalidate(membersProvider);
  }

  Future<void> _addMember() async {
    final name = _member.text.trim();
    if (name.isEmpty) return;
    final service = await ref.read(householdServiceProvider.future);
    await service.addMember(
      name,
      _memberChild ? MemberRole.child : MemberRole.adult,
    );
    _member.clear();
    ref.invalidate(membersProvider);
  }

  Future<void> _next() async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      if (_step == 1) await _saveOwner();
      if (_step < 3) {
        setState(() => _step++);
        return;
      }
      await _finish();
    } on Object {
      AppLog.event('onboarding_step_failed');
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(context.l10n.genericError)));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _finish() async {
    final l10n = context.l10n;
    final router = GoRouter.of(context);
    final service = await ref.read(householdServiceProvider.future);
    if (_kind == IncomeKind.salary) await service.setMonthStartDay(_salaryDay);
    await service.completeOnboarding(
      incomeKind: _kind!,
      at: ref.read(clockProvider).nowUtc(),
    );
    await syncIncomeReminder(ref, l10n);
    refreshMoneyViews(ref);
    ref
      ..invalidate(currentHouseholdProvider)
      ..invalidate(onboardedProvider);
    await ref.read(onboardedProvider.future);
    router.go(AppRoutes.home);
    // Faol qarz bo'lsa — darhol qarzlar bo'limi: qarz qo'shish va
    // «Qarzdan chiqish» (DEBT_RECOVERY) taklifi shu yerda.
    if (_hasDebt ?? false) {
      await Future<void>.delayed(Duration.zero);
      unawaited(router.push(AppRoutes.debts));
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    return PopScope(
      canPop: _step == 0,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop && _step > 0) setState(() => _step--);
      },
      child: Scaffold(
        appBar: AppBar(
          leading: _step == 0
              ? null
              : BackButton(onPressed: () => setState(() => _step--)),
          automaticallyImplyLeading: false,
          title: Text(
            l10n.obStep(_step + 2, OnboardingScreen.totalSteps),
            key: const Key('ob-step'),
          ),
        ),
        body: SafeArea(
          child: Column(
            children: [
              LinearProgressIndicator(
                value: (_step + 2) / OnboardingScreen.totalSteps,
              ),
              Expanded(
                child: Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 560),
                    child: ListView(
                      padding: const EdgeInsets.all(20),
                      children: switch (_step) {
                        0 => _language(l10n, theme),
                        1 => _family(l10n, theme),
                        2 => _income(l10n, theme),
                        _ => _debt(l10n, theme),
                      },
                    ),
                  ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 8, 20, 16),
                child: SizedBox(
                  width: double.infinity,
                  child: FilledButton(
                    key: const Key('ob-next'),
                    style: FilledButton.styleFrom(
                      minimumSize: const Size.fromHeight(56),
                    ),
                    onPressed: _canNext && !_busy ? _next : null,
                    child: Text(_step == 3 ? l10n.obFinish : l10n.obNext),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  List<Widget> _language(AppLocalizations l10n, ThemeData theme) {
    final lang = ref.watch(settingsControllerProvider).language;
    return [
      const BrandLogo(size: 64),
      const SizedBox(height: 16),
      Text(l10n.obWelcome, style: theme.textTheme.headlineSmall),
      const SizedBox(height: 24),
      Text(l10n.obLanguage, style: theme.textTheme.titleMedium),
      const SizedBox(height: 8),
      SegmentedButton<AppLanguage>(
        key: const Key('ob-language'),
        segments: [
          for (final l in AppLanguage.values)
            ButtonSegment(
              value: l,
              label: Text(lookupAppLocalizations(l.locale).languageName),
            ),
        ],
        selected: {lang},
        onSelectionChanged: (s) =>
            ref.read(settingsControllerProvider.notifier).setLanguage(s.single),
      ),
      const SizedBox(height: 8),
      Text(l10n.obLanguageHint, style: theme.textTheme.bodySmall),
      const SizedBox(height: 32),
      OutlinedButton.icon(
        key: const Key('ob-restore'),
        style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(52)),
        icon: const Icon(Icons.restore),
        label: Text(l10n.obRestore),
        onPressed: () => context.push(AppRoutes.backup),
      ),
    ];
  }

  List<Widget> _family(AppLocalizations l10n, ThemeData theme) {
    final members = ref.watch(membersProvider).valueOrNull ?? const [];
    final others = [
      for (final m in members)
        if (!m.isOwner) m,
    ];
    return [
      Text(l10n.obFamily, style: theme.textTheme.headlineSmall),
      const SizedBox(height: 8),
      Text(l10n.obFamilyHint),
      const SizedBox(height: 20),
      TextField(
        key: const Key('ob-owner'),
        controller: _owner,
        textCapitalization: TextCapitalization.words,
        decoration: InputDecoration(
          labelText: l10n.obOwnerName,
          hintText: l10n.memberOwnerDefault,
        ),
      ),
      const SizedBox(height: 20),
      for (final m in others)
        Card(
          child: ListTile(
            leading: ExcludeSemantics(
              child: CircleAvatar(
                child: Text(m.displayName.characters.first.toUpperCase()),
              ),
            ),
            title: Text(m.displayName),
            subtitle: Text(
              m.role == MemberRole.child
                  ? l10n.obMemberChild
                  : l10n.obMemberAdult,
            ),
            trailing: IconButton(
              tooltip: l10n.obMemberRemove,
              icon: const Icon(Icons.close),
              onPressed: () async {
                await (await ref.read(
                  householdServiceProvider.future,
                )).remove(m);
                ref.invalidate(membersProvider);
              },
            ),
          ),
        ),
      TextField(
        key: const Key('ob-member-name'),
        controller: _member,
        textCapitalization: TextCapitalization.words,
        decoration: InputDecoration(labelText: l10n.memberName),
        onSubmitted: (_) => _addMember(),
      ),
      const SizedBox(height: 8),
      Wrap(
        spacing: 8,
        runSpacing: 8,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          ChoiceChip(
            label: Text(l10n.obMemberAdult),
            selected: !_memberChild,
            onSelected: (_) => setState(() => _memberChild = false),
          ),
          ChoiceChip(
            label: Text(l10n.obMemberChild),
            selected: _memberChild,
            onSelected: (_) => setState(() => _memberChild = true),
          ),
          TextButton.icon(
            key: const Key('ob-member-add'),
            style: TextButton.styleFrom(minimumSize: const Size(48, 48)),
            icon: const Icon(Icons.add),
            label: Text(l10n.obAddMember),
            onPressed: _addMember,
          ),
        ],
      ),
    ];
  }

  Widget _choice({
    required Key key,
    required bool selected,
    required IconData icon,
    required String title,
    required String? hint,
    required VoidCallback onTap,
  }) {
    final scheme = Theme.of(context).colorScheme;
    return Card(
      key: key,
      color: selected ? scheme.primaryContainer : null,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(
          color: selected ? scheme.primary : scheme.outlineVariant,
          width: selected ? 2 : 1,
        ),
      ),
      child: Semantics(
        selected: selected,
        child: ListTile(
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 16,
            vertical: 8,
          ),
          leading: Icon(icon),
          title: Text(title),
          subtitle: hint == null ? null : Text(hint),
          trailing: selected ? const Icon(Icons.check_circle) : null,
          onTap: onTap,
        ),
      ),
    );
  }

  List<Widget> _income(AppLocalizations l10n, ThemeData theme) => [
    Text(l10n.obIncome, style: theme.textTheme.headlineSmall),
    const SizedBox(height: 8),
    Text(l10n.obIncomeHint),
    const SizedBox(height: 16),
    for (final (kind, icon, title, hint) in [
      (
        IncomeKind.dailyCash,
        Icons.payments_outlined,
        l10n.obIncomeDaily,
        l10n.obIncomeDailyHint,
      ),
      (
        IncomeKind.orders,
        Icons.assignment_outlined,
        l10n.obIncomeOrders,
        l10n.obIncomeOrdersHint,
      ),
      (
        IncomeKind.salary,
        Icons.calendar_month_outlined,
        l10n.obIncomeSalary,
        l10n.obIncomeSalaryHint,
      ),
    ])
      _choice(
        key: Key('ob-income-${kind.name}'),
        selected: _kind == kind,
        icon: icon,
        title: title,
        hint: hint,
        onTap: () => setState(() => _kind = kind),
      ),
    if (_kind == IncomeKind.salary) ...[
      const SizedBox(height: 12),
      Row(
        children: [
          Expanded(child: Text(l10n.obSalaryDay)),
          DropdownButton<int>(
            key: const Key('ob-salary-day'),
            value: _salaryDay,
            items: [
              for (var d = 1; d <= 31; d++)
                DropdownMenuItem(value: d, child: Text('$d')),
            ],
            onChanged: (d) => setState(() => _salaryDay = d ?? _salaryDay),
          ),
        ],
      ),
    ],
  ];

  List<Widget> _debt(AppLocalizations l10n, ThemeData theme) => [
    Text(l10n.obDebt, style: theme.textTheme.headlineSmall),
    const SizedBox(height: 8),
    Text(l10n.obDebtHint),
    const SizedBox(height: 16),
    _choice(
      key: const Key('ob-debt-yes'),
      selected: _hasDebt ?? false,
      icon: Icons.receipt_long_outlined,
      title: l10n.obDebtYes,
      hint: l10n.obDebtRecovery,
      onTap: () => setState(() => _hasDebt = true),
    ),
    _choice(
      key: const Key('ob-debt-no'),
      selected: _hasDebt == false,
      icon: Icons.check_circle_outline,
      title: l10n.obDebtNo,
      hint: null,
      onTap: () => setState(() => _hasDebt = false),
    ),
  ];
}
