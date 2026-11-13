import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:zanjir_core/zanjir_core.dart' show Ed25519Signer;
import 'package:zanjir_data/zanjir_data.dart';

import '../../core/numbers.dart';
import '../../core/providers.dart';
import '../../l10n/gen/app_localizations.dart';
import '../../l10n/labels.dart';
import '../../theme/tokens.dart';
import '../../widgets/async_view.dart';
import '../../widgets/password_prompt.dart';

/// Xodimlar, qurilmalar va telefonlar o'rtasida fayl almashish (ADR-0017 8-band). Server yo'q: ma'lumot faqat
/// imzolangan va shifrlangan fayl orqali o'tadi, import barcha tekshiruvlardan o'tmasa — hech narsa yozilmaydi.
class StaffScreen extends ConsumerWidget {
  const StaffScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final profile = ref.watch(profileProvider).value;
    final canEdit = profile?.canEditSettings ?? false;
    final titleStyle = Theme.of(context).textTheme.titleMedium;
    return Scaffold(
      appBar: AppBar(title: Text(l10n.staffTitle)),
      body: ListView(
        padding: const EdgeInsets.only(bottom: 24),
        children: [
          ListTile(
            title: Text(l10n.exchangeSection, style: titleStyle),
            subtitle: Text(l10n.exchangeHint),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Wrap(
              spacing: 12,
              runSpacing: 8,
              children: [
                FilledButton.icon(
                  key: const Key('exchange.export'),
                  onPressed: () => _export(context, ref),
                  icon: const Icon(Icons.upload_file),
                  label: Text(l10n.exchangeExport),
                ),
                OutlinedButton.icon(
                  key: const Key('exchange.import'),
                  onPressed: () => _import(context, ref, canEdit: canEdit),
                  icon: const Icon(Icons.download),
                  label: Text(l10n.exchangeImport),
                ),
              ],
            ),
          ),
          const Divider(height: 32),
          ListTile(
            title: Text(l10n.staffSection, style: titleStyle),
            trailing: canEdit
                ? IconButton(
                    key: const Key('staff.add'),
                    tooltip: l10n.staffAdd,
                    icon: const Icon(Icons.person_add),
                    onPressed: () => showDialog<void>(context: context, builder: (_) => const _AddUserDialog()),
                  )
                : null,
          ),
          AsyncView(
            value: ref.watch(staffProvider),
            builder: (users) => Column(
              children: [
                for (final u in users)
                  ListTile(
                    leading: const Icon(Icons.person),
                    title: Text(u.fullName),
                    subtitle: Text(l10n.roleName(u.role)),
                    trailing: canEdit && u.id != profile?.userId
                        ? IconButton(
                            key: Key('staff.invite.${u.id}'),
                            tooltip: l10n.staffInvite,
                            icon: const Icon(Icons.forward_to_inbox),
                            onPressed: () => _invite(context, ref, u),
                          )
                        : null,
                  ),
              ],
            ),
          ),
          const Divider(height: 32),
          ListTile(title: Text(l10n.devicesSection, style: titleStyle)),
          AsyncView(
            value: ref.watch(devicesProvider),
            builder: (devices) {
              final names = {for (final u in ref.watch(staffProvider).value ?? const <AppUserRow>[]) u.id: u.fullName};
              return Column(
                children: [
                  for (final d in devices)
                    ListTile(
                      leading: Icon(
                        d.revokedAt == null ? Icons.smartphone : Icons.phonelink_erase,
                        color: d.revokedAt == null ? null : ZanjirColors.danger,
                      ),
                      title: Text(names[d.userId] ?? d.userId),
                      subtitle: Text(
                        [
                          formatLocalDateTime(d.registeredAt),
                          if (d.id == profile?.deviceId) l10n.deviceThis,
                          if (d.revokedAt != null) l10n.deviceRevoked,
                        ].join(' · '),
                      ),
                      trailing: canEdit && d.id != profile?.deviceId && d.revokedAt == null
                          ? IconButton(
                              key: Key('device.revoke.${d.id}'),
                              tooltip: l10n.deviceRevoke,
                              icon: const Icon(Icons.block),
                              onPressed: () => _revoke(context, ref, d),
                            )
                          : null,
                    ),
                ],
              );
            },
          ),
        ],
      ),
    );
  }

  Future<Ed25519Signer> _signer(WidgetRef ref) async =>
      Ed25519Signer.fromSeed((await ref.read(keyStoreProvider).readSeed())!);

  Future<void> _export(BuildContext context, WidgetRef ref) async {
    final l10n = AppLocalizations.of(context);
    final messenger = ScaffoldMessenger.of(context);
    try {
      final repos = await ref.read(repositoriesProvider.future);
      final profile = (await ref.read(profileProvider.future))!;
      final signer = await _signer(ref);
      if (!context.mounted) return;
      final bytes = await withProgress(
        context,
        l10n.exchangeWorking,
        () => createExchangeFile(repos.ctx, signer: signer, deviceId: profile.deviceId),
      );
      final name = 'zanjir-almashish-${_stamp(ref)}.$exchangeFileExtension';
      if (await ref.read(fileActionsProvider).save(bytes, name)) {
        messenger.showSnackBar(SnackBar(content: Text(l10n.exchangeSaved)));
      }
    } catch (e) {
      messenger.showSnackBar(SnackBar(content: Text(l10n.importErrorText(e))));
    }
  }

  Future<void> _import(BuildContext context, WidgetRef ref, {required bool canEdit}) async {
    final l10n = AppLocalizations.of(context);
    final messenger = ScaffoldMessenger.of(context);
    try {
      final bytes = await ref.read(fileActionsProvider).pick();
      if (bytes == null || !context.mounted) return;
      if (readExchangeHeader(bytes).kind == ExchangeKind.invite) {
        throw const DataRuleException('exchange_is_invite');
      }
      final approve = <String>{};
      // Tasdiqlanmagan qurilma (zaxiradan tiklangan telefon) — LEAD/ADMIN yuzma-yuz tekshirib tasdiqlaydi.
      for (var attempt = 0; ; attempt++) {
        try {
          final result = await withProgress(
            context,
            l10n.importWorking,
            () => importExchangeFile(ref, bytes, approve: approve),
          );
          messenger.showSnackBar(
            SnackBar(content: Text(result.total == 0 ? l10n.importNothing : l10n.importDone(result.total))),
          );
          return;
        } on DataRuleException catch (e) {
          final id = e.detail;
          if (e.code != 'device_not_approved' || !canEdit || id == null || attempt >= 5 || !context.mounted) rethrow;
          final ok = await showDialog<bool>(
            context: context,
            builder: (dialog) => AlertDialog(
              title: Text(l10n.deviceApproveTitle),
              content: Text(l10n.deviceApproveHint),
              actions: [
                TextButton(onPressed: () => Navigator.pop(dialog, false), child: Text(l10n.cancel)),
                FilledButton(
                  key: const Key('device.approve'),
                  onPressed: () => Navigator.pop(dialog, true),
                  child: Text(l10n.approve),
                ),
              ],
            ),
          );
          if (ok != true || !context.mounted) return;
          approve.add(id);
        }
      }
    } catch (e) {
      messenger.showSnackBar(SnackBar(content: Text(l10n.importErrorText(e))));
    }
  }

  Future<void> _invite(BuildContext context, WidgetRef ref, AppUserRow user) async {
    final l10n = AppLocalizations.of(context);
    final messenger = ScaffoldMessenger.of(context);
    try {
      final repos = await ref.read(repositoriesProvider.future);
      final profile = (await ref.read(profileProvider.future))!;
      final signer = await _signer(ref);
      final inviteId = await repos.staff.createInvite(user.id);
      final password = newInvitePassword();
      if (!context.mounted) return;
      final bytes = await withProgress(
        context,
        l10n.exchangeWorking,
        () => createInviteFile(
          repos.ctx,
          signer: signer,
          deviceId: profile.deviceId,
          inviteId: inviteId,
          userId: user.id,
          password: password,
          kdf: ref.read(backupKdfProvider),
        ),
      );
      final name = 'zanjir-taklif-${_stamp(ref)}.$exchangeFileExtension';
      if (!await ref.read(fileActionsProvider).save(bytes, name) || !context.mounted) return;
      // Parol ekranda — ekranshot va yozuvdan himoya.
      final secure = ref.read(secureScreenProvider);
      await secure.enable();
      try {
        if (!context.mounted) return;
        await showDialog<void>(
          context: context,
          builder: (dialog) => AlertDialog(
            title: Text(l10n.inviteTitle),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(l10n.inviteHint(user.fullName)),
                const SizedBox(height: 16),
                SelectableText(
                  password,
                  key: const Key('invite.password'),
                  textAlign: TextAlign.center,
                  style: Theme.of(dialog).textTheme.headlineSmall
                      ?.copyWith(fontFamily: 'monospace', letterSpacing: 2, color: ZanjirColors.accentText),
                ),
              ],
            ),
            actions: [FilledButton(onPressed: () => Navigator.pop(dialog), child: Text(l10n.close))],
          ),
        );
      } finally {
        await secure.disable();
      }
    } catch (e) {
      messenger.showSnackBar(SnackBar(content: Text(l10n.errorText(e))));
    }
  }

  Future<void> _revoke(BuildContext context, WidgetRef ref, DeviceRow device) async {
    final l10n = AppLocalizations.of(context);
    final messenger = ScaffoldMessenger.of(context);
    final ok = await showDialog<bool>(
      context: context,
      builder: (dialog) => AlertDialog(
        title: Text(l10n.deviceRevoke),
        content: Text(l10n.deviceRevokeConfirm),
        actions: [
          TextButton(onPressed: () => Navigator.pop(dialog, false), child: Text(l10n.cancel)),
          FilledButton(
            key: const Key('device.revokeConfirm'),
            style: FilledButton.styleFrom(
              backgroundColor: ZanjirColors.danger,
              foregroundColor: ZanjirColors.accentInk,
            ),
            onPressed: () => Navigator.pop(dialog, true),
            child: Text(l10n.deviceRevoke),
          ),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await (await ref.read(repositoriesProvider.future)).staff.revokeDevice(device.id);
      ref.invalidate(devicesProvider);
    } catch (e) {
      messenger.showSnackBar(SnackBar(content: Text(l10n.errorText(e))));
    }
  }

  String _stamp(WidgetRef ref) =>
      formatLocalDateTime(ref.read(clockProvider)()).replaceAll(':', '').replaceAll(' ', '-');
}

class _AddUserDialog extends ConsumerStatefulWidget {
  const _AddUserDialog();

  @override
  ConsumerState<_AddUserDialog> createState() => _AddUserDialogState();
}

class _AddUserDialogState extends ConsumerState<_AddUserDialog> {
  final _form = GlobalKey<FormState>();
  final _name = TextEditingController();
  String _role = 'ENGINEER';

  @override
  void dispose() {
    _name.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!_form.currentState!.validate()) return;
    final l10n = AppLocalizations.of(context);
    try {
      final repos = await ref.read(repositoriesProvider.future);
      await repos.staff.addUser(fullName: _name.text, role: _role);
      ref.invalidate(staffProvider);
      if (mounted) Navigator.pop(context);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l10n.errorText(e))));
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return AlertDialog(
      title: Text(l10n.staffAdd),
      content: Form(
        key: _form,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextFormField(
              key: const Key('staff.name'),
              controller: _name,
              decoration: InputDecoration(labelText: l10n.fullName),
              autofocus: true,
              validator: (v) => (v ?? '').trim().isEmpty ? l10n.requiredField : null,
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              key: const Key('staff.role'),
              initialValue: _role,
              decoration: InputDecoration(labelText: l10n.role),
              items: [for (final r in StaffRepository.roles) DropdownMenuItem(value: r, child: Text(l10n.roleName(r)))],
              onChanged: (v) => setState(() => _role = v ?? _role),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: Text(l10n.cancel)),
        FilledButton(key: const Key('staff.save'), onPressed: _save, child: Text(l10n.save)),
      ],
    );
  }
}
