import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/refresh.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/features/debts/data/debt_providers.dart';
import 'package:baraka_daftari/features/debts/domain/debt_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Qarz yopilganda nishonlash (SPEC 2D.9) — faqat `result.closed` bo'lsa.
Future<void> showDebtClosed(
  NavigatorState navigator,
  WidgetRef ref,
  DebtPaymentResult result,
) async {
  if (!result.closed) return;
  final split = (await ref.read(recoveryStateProvider.future)).split;
  await navigator.push<void>(
    MaterialPageRoute(
      fullscreenDialog: true,
      builder: (_) => DebtClosedScreen(result: result, freedBp: split.debtBp),
    ),
  );
}

/// «Alhamdulillah! Qarz yopildi»: bo'shagan oylik to'lovni (yoki rejim
/// tugaganda 20 % ulushni) «Kelajagim»ga yo'naltirish taklifi.
class DebtClosedScreen extends ConsumerStatefulWidget {
  const DebtClosedScreen({
    required this.result,
    required this.freedBp,
    super.key,
  });

  final DebtPaymentResult result;

  /// Rejim ulushi (bo'shagan 20 %).
  final int freedBp;

  @override
  ConsumerState<DebtClosedScreen> createState() => _DebtClosedScreenState();
}

class _DebtClosedScreenState extends ConsumerState<DebtClosedScreen> {
  String? _message;
  bool _busy = false;

  Future<void> _redirect() async {
    final l10n = context.l10n;
    setState(() => _busy = true);
    try {
      final recovery = await ref.read(recoveryServiceProvider.future);
      final r = widget.result;
      final rule = r.modeReturned
          ? await recovery.acceptFreedShare()
          : await recovery.redirectFreed(r.freedMonthly!);
      refreshMoneyViews(ref);
      setState(
        () => _message = rule == null
            ? l10n.debtClosedNoIncome
            : l10n.debtClosedRedirected,
      );
    } on Object {
      AppLog.event('debt_freed_redirect_failed');
      setState(() => _message = l10n.genericError);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _close() async {
    final navigator = Navigator.of(context);
    if (widget.result.modeReturned && _message == null) {
      // Taklif rad etildi — keyin bosh ekranda qayta so'ralmaydi.
      await (await ref.read(
        recoveryServiceProvider.future,
      )).dismissFreedShare();
      refreshMoneyViews(ref);
    }
    navigator.pop();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final money = context.money;
    final r = widget.result;
    final freed = r.freedMonthly;
    final canRedirect = r.modeReturned || (freed != null && freed.isPositive);
    return Scaffold(
      appBar: AppBar(automaticallyImplyLeading: false),
      body: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          Icon(Icons.task_alt, size: 72, color: theme.colorScheme.primary),
          const SizedBox(height: 16),
          Text(
            l10n.debtClosedTitle,
            key: const Key('debt-closed-title'),
            style: theme.textTheme.headlineSmall,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 8),
          Text(
            l10n.debtClosedBody(r.debt.creditorName),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 24),
          if (r.modeReturned) ...[
            Text(l10n.modeReturned, key: const Key('debt-mode-returned')),
            const SizedBox(height: 8),
            Text(l10n.freedShareBody(percentLabel(widget.freedBp))),
          ] else if (freed != null && freed.isPositive)
            Text(l10n.debtClosedFreed(money(freed))),
          const SizedBox(height: 16),
          if (_message != null)
            Text(
              _message!,
              key: const Key('debt-closed-message'),
              style: TextStyle(color: theme.colorScheme.primary),
            )
          else if (canRedirect)
            FilledButton(
              key: const Key('debt-closed-redirect'),
              onPressed: _busy ? null : _redirect,
              child: Text(l10n.freedShareAccept),
            ),
          const SizedBox(height: 8),
          TextButton(
            key: const Key('debt-closed-done'),
            onPressed: _busy ? null : _close,
            child: Text(
              _message == null && canRedirect
                  ? l10n.notNow
                  : l10n.debtClosedDone,
            ),
          ),
        ],
      ),
    );
  }
}
