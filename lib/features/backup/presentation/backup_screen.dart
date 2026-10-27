import 'dart:typed_data';

import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/refresh.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/backup/data/backup_providers.dart';
import 'package:baraka_daftari/features/backup/domain/backup_service.dart';
import 'package:baraka_daftari/features/onboarding/data/onboarding_providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// Shifrlangan zaxira nusxa (MVP_PLAN Vazifa 15): butun daftar parol bilan
/// shifrlangan `.bkd` faylga; tiklash shu fayl va parol bilan (to'liq
/// almashtirish). Onboarding'dan ham ochiladi.
class BackupScreen extends ConsumerStatefulWidget {
  const BackupScreen({super.key});

  @override
  ConsumerState<BackupScreen> createState() => _BackupScreenState();
}

class _BackupScreenState extends ConsumerState<BackupScreen> {
  final _password = TextEditingController();
  final _repeat = TextEditingController();
  String? _busy;
  String? _error;

  @override
  void dispose() {
    _password.dispose();
    _repeat.dispose();
    super.dispose();
  }

  String _message(AppLocalizations l10n, String code) => switch (code) {
    BackupService.errWeakPassword => l10n.backupPassword,
    BackupService.errBadPassword => l10n.backupBadPassword,
    BackupService.errVersion => l10n.backupVersion,
    BackupService.errFormat => l10n.backupBadFormat,
    _ => l10n.genericError,
  };

  bool get _exportReady =>
      _password.text.length >= BackupService.minPassword &&
      _password.text == _repeat.text;

  Future<void> _export() async {
    final l10n = context.l10n;
    if (_password.text != _repeat.text) {
      setState(() => _error = l10n.backupPasswordMismatch);
      return;
    }
    setState(() {
      _busy = l10n.backupWorking;
      _error = null;
    });
    try {
      final service = await ref.read(backupServiceProvider.future);
      final bytes = await service.export(_password.text);
      final d = ref.read(clockProvider).nowUtc().toLocal();
      String two(int v) => v.toString().padLeft(2, '0');
      final name =
          'baraka_${d.year}${two(d.month)}${two(d.day)}_'
          '${two(d.hour)}${two(d.minute)}.bkd';
      await ref.read(backupSaverProvider)(bytes, name);
      _password.clear();
      _repeat.clear();
    } on DomainRuleException catch (e) {
      setState(() => _error = _message(l10n, e.code));
    } on Object {
      AppLog.event('backup_export_failed');
      setState(() => _error = l10n.genericError);
    } finally {
      if (mounted) setState(() => _busy = null);
    }
  }

  Future<String?> _askPassword() => showDialog<String>(
    context: context,
    builder: (_) => const _PasswordDialog(),
  );

  Future<void> _import() async {
    final l10n = context.l10n;
    final messenger = ScaffoldMessenger.of(context);
    final router = GoRouter.of(context);
    setState(() => _error = null);
    final Uint8List? data;
    try {
      data = await ref.read(backupPickerProvider)();
    } on Object {
      AppLog.event('backup_pick_failed');
      setState(() => _error = l10n.genericError);
      return;
    }
    if (data == null || !mounted) return;
    final password = await _askPassword();
    if (password == null || password.isEmpty || !mounted) return;
    final ok = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        content: Text(l10n.backupImportConfirm),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text(l10n.cancel),
          ),
          FilledButton(
            key: const Key('backup-import-confirm'),
            onPressed: () => Navigator.pop(context, true),
            child: Text(l10n.backupImport),
          ),
        ],
      ),
    );
    if (ok != true || !mounted) return;
    setState(() => _busy = l10n.backupRestoring);
    try {
      final service = await ref.read(backupServiceProvider.future);
      final rows = await service.import(data, password);
      refreshMoneyViews(ref);
      ref
        ..invalidate(currentHouseholdProvider)
        ..invalidate(onboardedProvider);
      await ref.read(onboardedProvider.future);
      messenger.showSnackBar(
        SnackBar(content: Text(l10n.backupRestored(rows))),
      );
      router.go(AppRoutes.home);
    } on DomainRuleException catch (e) {
      if (mounted) setState(() => _error = _message(l10n, e.code));
    } on Object {
      AppLog.event('backup_import_failed');
      if (mounted) setState(() => _error = l10n.genericError);
    } finally {
      if (mounted) setState(() => _busy = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final busy = _busy;
    return Scaffold(
      appBar: AppBar(title: Text(l10n.backupTitle)),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 620),
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Text(l10n.backupHint),
              const SizedBox(height: 16),
              if (busy != null) ...[
                const LinearProgressIndicator(),
                const SizedBox(height: 8),
                Text(busy, key: const Key('backup-busy')),
                const SizedBox(height: 16),
              ],
              if (_error case final error?) ...[
                Text(
                  error,
                  key: const Key('backup-error'),
                  style: TextStyle(color: theme.colorScheme.error),
                ),
                const SizedBox(height: 16),
              ],
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text(
                        l10n.backupExportTitle,
                        style: theme.textTheme.titleMedium,
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        key: const Key('backup-password'),
                        controller: _password,
                        obscureText: true,
                        decoration: InputDecoration(
                          labelText: l10n.backupPassword,
                        ),
                        onChanged: (_) => setState(() {}),
                      ),
                      const SizedBox(height: 8),
                      TextField(
                        key: const Key('backup-password-repeat'),
                        controller: _repeat,
                        obscureText: true,
                        decoration: InputDecoration(
                          labelText: l10n.backupPasswordRepeat,
                          errorText:
                              _repeat.text.isNotEmpty &&
                                  _repeat.text != _password.text
                              ? l10n.backupPasswordMismatch
                              : null,
                        ),
                        onChanged: (_) => setState(() {}),
                      ),
                      const SizedBox(height: 16),
                      FilledButton.icon(
                        key: const Key('backup-export'),
                        style: FilledButton.styleFrom(
                          minimumSize: const Size.fromHeight(52),
                        ),
                        icon: const Icon(Icons.lock_outline),
                        label: Text(l10n.backupExport),
                        onPressed: _exportReady && busy == null
                            ? _export
                            : null,
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 12),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text(
                        l10n.backupImportTitle,
                        style: theme.textTheme.titleMedium,
                      ),
                      const SizedBox(height: 8),
                      Text(l10n.backupImportHint),
                      const SizedBox(height: 16),
                      OutlinedButton.icon(
                        key: const Key('backup-import'),
                        style: OutlinedButton.styleFrom(
                          minimumSize: const Size.fromHeight(52),
                        ),
                        icon: const Icon(Icons.restore),
                        label: Text(l10n.backupImport),
                        onPressed: busy == null ? _import : null,
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Nusxa parolini so'rash (controller dialog bilan birga yashaydi —
/// yopilish animatsiyasida ham ishlatiladi).
class _PasswordDialog extends StatefulWidget {
  const _PasswordDialog();

  @override
  State<_PasswordDialog> createState() => _PasswordDialogState();
}

class _PasswordDialogState extends State<_PasswordDialog> {
  final _controller = TextEditingController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return AlertDialog(
      title: Text(l10n.backupImportPassword),
      content: TextField(
        key: const Key('backup-import-password'),
        controller: _controller,
        obscureText: true,
        autofocus: true,
        decoration: InputDecoration(labelText: l10n.backupPassword),
        onSubmitted: (v) => Navigator.pop(context, v),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text(l10n.cancel),
        ),
        FilledButton(
          key: const Key('backup-import-ok'),
          onPressed: () => Navigator.pop(context, _controller.text),
          child: Text(l10n.backupImport),
        ),
      ],
    );
  }
}
