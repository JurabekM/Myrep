import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:zanjir_data/zanjir_data.dart';

import '../../core/numbers.dart';
import '../../core/providers.dart';
import '../../core/sync_controller.dart';
import '../../l10n/gen/app_localizations.dart';
import '../../l10n/labels.dart';
import '../../theme/tokens.dart';
import '../../widgets/async_view.dart';

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final profile = ref.watch(profileProvider).value;
    final locale = ref.watch(localeProvider).value ?? 'uz';
    final largeText = ref.watch(largeTextProvider).value ?? false;
    final canEdit = profile?.canEditSettings ?? false;
    final now = ref.watch(clockProvider)();
    return Scaffold(
      appBar: AppBar(title: Text(l10n.settingsTitle)),
      body: ListView(
        padding: const EdgeInsets.only(bottom: 24),
        children: [
          if (profile != null)
            ListTile(
              leading: const Icon(Icons.person),
              title: Text(profile.fullName),
              subtitle: Text('${l10n.profile} · ${l10n.roleName(profile.role)}'),
            ),
          // Tanlov pastki qatorda — katta shriftda ham sig'adi (ADR-0014).
          ListTile(
            title: Text(l10n.language),
            subtitle: Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Align(
                alignment: AlignmentDirectional.centerStart,
                child: SegmentedButton<String>(
                  segments: [
                    ButtonSegment(value: 'uz', label: Text(l10n.languageUz)),
                    ButtonSegment(value: 'ru', label: Text(l10n.languageRu)),
                  ],
                  selected: {locale},
                  onSelectionChanged: (s) => ref.read(localeProvider.notifier).set(s.first),
                ),
              ),
            ),
          ),
          SwitchListTile(
            key: const Key('settings.largeText'),
            value: largeText,
            title: Text(l10n.largeText),
            onChanged: (v) => ref.read(largeTextProvider.notifier).set(v),
          ),
          const Divider(),
          AsyncView(
            value: ref.watch(organizationProvider),
            builder: (org) => ListTile(
              key: const Key('settings.lab'),
              leading: const Icon(Icons.science),
              trailing: canEdit
                  ? IconButton(
                      key: const Key('settings.editLab'),
                      tooltip: l10n.editLab,
                      icon: const Icon(Icons.edit),
                      onPressed: () => showDialog<void>(
                        context: context,
                        builder: (_) => _LabDialog(org: org),
                      ),
                    )
                  : null,
              title: Text('${l10n.lab}: ${org.name}'),
              subtitle: Text(
                [
                  if (org.licenseNo != null) '${l10n.licenseNo}: ${org.licenseNo}',
                  if (org.licenseValidUntil != null) formatIsoDate(org.licenseValidUntil!),
                ].join(' · '),
              ),
            ),
          ),
          const _ServerSection(),
          const Divider(),
          AsyncView(
            value: ref.watch(activeNormSetProvider),
            builder: (set) => ListTile(
              leading: Icon(
                set.isReviewed ? Icons.verified : Icons.report,
                color: set.isReviewed ? ZanjirColors.success : ZanjirColors.warn,
              ),
              title: Text(l10n.normsVersion(set.version)),
              subtitle: Text(
                set.isReviewed ? l10n.normsReviewed(set.reviewedBy, set.reviewedAt) : l10n.normsNotReviewed,
                style: TextStyle(color: set.isReviewed ? null : ZanjirColors.warn),
              ),
            ),
          ),
          const Divider(),
          ListTile(title: Text(l10n.evalSettings, style: Theme.of(context).textTheme.titleMedium)),
          AsyncView(
            value: ref.watch(labSettingsProvider),
            builder: (s) => _EvalSettingsForm(settings: s, enabled: canEdit),
          ),
          const Divider(),
          ListTile(
            title: Text(l10n.instruments, style: Theme.of(context).textTheme.titleMedium),
            trailing: IconButton(
              key: const Key('settings.addInstrument'),
              tooltip: l10n.addInstrument,
              icon: const Icon(Icons.add),
              onPressed: () => context.push('/settings/instruments/new'),
            ),
          ),
          AsyncView(
            value: ref.watch(instrumentsProvider),
            builder: (list) => Column(
              children: [
                for (final i in list)
                  ListTile(
                    leading: Icon(
                      instrumentVerificationValid(i, now) ? Icons.check : Icons.event_busy,
                      color: instrumentVerificationValid(i, now) ? ZanjirColors.success : ZanjirColors.warn,
                    ),
                    title: Text('${i.model} · ${i.serialNo}'),
                    subtitle: Text(
                      [
                        i.kind,
                        if (i.verificationCertNo != null) i.verificationCertNo!,
                        if (i.verifiedUntil != null) formatIsoDate(i.verifiedUntil!),
                        if (!instrumentVerificationValid(i, now)) l10n.instrumentExpired,
                      ].join(' · '),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _EvalSettingsForm extends ConsumerStatefulWidget {
  const _EvalSettingsForm({required this.settings, required this.enabled});
  final LabSettings settings;
  final bool enabled;

  @override
  ConsumerState<_EvalSettingsForm> createState() => _EvalSettingsFormState();
}

class _EvalSettingsFormState extends ConsumerState<_EvalSettingsForm> {
  final _form = GlobalKey<FormState>();
  late final _kCorr = TextEditingController(text: formatDecimal(widget.settings.kCorr));
  late final _margin = TextEditingController(text: formatDecimal(widget.settings.marginPct));

  @override
  void dispose() {
    _kCorr.dispose();
    _margin.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!_form.currentState!.validate()) return;
    final l10n = AppLocalizations.of(context);
    try {
      final repos = await ref.read(repositoriesProvider.future);
      final profile = (await ref.read(profileProvider.future))!;
      await repos.settings.update(
        byUserId: profile.userId,
        kCorr: parseDecimal(_kCorr.text),
        marginPct: parseDecimal(_margin.text),
      );
      ref.invalidate(labSettingsProvider);
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l10n.settingsSaved)));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l10n.errorText(e))));
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    String? kCorrRule(String? v) {
      final k = parseDecimal(v);
      return k != null && k > 0 && k <= 1 ? null : l10n.invalidKCorr;
    }

    String? marginRule(String? v) {
      final m = parseDecimal(v);
      return m != null && m >= 0 && m <= 50 ? null : l10n.invalidMargin;
    }

    return Form(
      key: _form,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (!widget.enabled) Text(l10n.leadOnly, style: const TextStyle(color: ZanjirColors.inkMuted)),
            const SizedBox(height: 8),
            TextFormField(
              key: const Key('settings.kCorr'),
              controller: _kCorr,
              enabled: widget.enabled,
              decoration: InputDecoration(labelText: l10n.kCorr),
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              validator: kCorrRule,
            ),
            const SizedBox(height: 12),
            TextFormField(
              key: const Key('settings.margin'),
              controller: _margin,
              enabled: widget.enabled,
              decoration: InputDecoration(labelText: l10n.marginPct),
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              validator: marginRule,
            ),
            const SizedBox(height: 12),
            if (widget.enabled)
              FilledButton(key: const Key('settings.saveEval'), onPressed: _save, child: Text(l10n.save)),
          ],
        ),
      ),
    );
  }
}

/// Laboratoriya rekvizitlari: nomi, litsenziya raqami va muddati (protokol imzolash sharti) — faqat LEAD/ADMIN.
class _LabDialog extends ConsumerStatefulWidget {
  const _LabDialog({required this.org});
  final OrganizationRow org;

  @override
  ConsumerState<_LabDialog> createState() => _LabDialogState();
}

class _LabDialogState extends ConsumerState<_LabDialog> {
  final _form = GlobalKey<FormState>();
  late final _name = TextEditingController(text: widget.org.name);
  late final _license = TextEditingController(text: widget.org.licenseNo ?? '');
  late final _until = TextEditingController(
    text: widget.org.licenseValidUntil == null ? '' : formatIsoDate(widget.org.licenseValidUntil!),
  );

  @override
  void dispose() {
    _name.dispose();
    _license.dispose();
    _until.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!_form.currentState!.validate()) return;
    final l10n = AppLocalizations.of(context);
    try {
      final repos = await ref.read(repositoriesProvider.future);
      final profile = (await ref.read(profileProvider.future))!;
      await repos.settings.updateLab(
        byUserId: profile.userId,
        name: _name.text.trim(),
        licenseNo: _license.text.trim().isEmpty ? null : _license.text.trim(),
        licenseValidUntil: parseIsoDate(_until.text),
      );
      ref.invalidate(organizationProvider);
      ref.invalidate(protocolDraftProvider);
      if (mounted) Navigator.pop(context);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l10n.errorText(e))));
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return AlertDialog(
      title: Text(l10n.editLab),
      content: Form(
        key: _form,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextFormField(
                key: const Key('lab.name'),
                controller: _name,
                decoration: InputDecoration(labelText: l10n.labName),
                validator: (v) => (v ?? '').trim().isEmpty ? l10n.requiredField : null,
              ),
              TextFormField(
                key: const Key('lab.license'),
                controller: _license,
                decoration: InputDecoration(labelText: l10n.licenseNo),
              ),
              TextFormField(
                key: const Key('lab.until'),
                controller: _until,
                decoration: InputDecoration(labelText: l10n.licenseValidUntil),
                keyboardType: TextInputType.datetime,
                validator: (v) => (v ?? '').trim().isEmpty || parseIsoDate(v) != null ? null : l10n.invalidDate,
              ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: Text(l10n.cancel)),
        FilledButton(key: const Key('lab.save'), onPressed: _save, child: Text(l10n.save)),
      ],
    );
  }
}

/// Server bilan ulanish va sinxronlash (ADR-0012).
class _ServerSection extends ConsumerWidget {
  const _ServerSection();

  Future<void> _register(BuildContext context, WidgetRef ref) async {
    final l10n = AppLocalizations.of(context);
    final password = await showDialog<String>(context: context, builder: (_) => const _PasswordDialog());
    if (password == null || !context.mounted) return;
    try {
      await ref.read(syncControllerProvider.notifier).registerLab(password);
    } catch (e) {
      if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l10n.serverErrorText(e))));
    }
  }

  Future<void> _invite(BuildContext context, WidgetRef ref) async {
    final l10n = AppLocalizations.of(context);
    final role = await showDialog<String>(
      context: context,
      builder: (ctx) => SimpleDialog(
        title: Text(l10n.createInvite),
        children: [
          for (final r in ['ENGINEER', 'VIEWER', 'LEAD'])
            SimpleDialogOption(
              key: Key('invite.role.$r'),
              onPressed: () => Navigator.pop(ctx, r),
              child: Text(l10n.roleName(r)),
            ),
        ],
      ),
    );
    if (role == null || !context.mounted) return;
    try {
      final code = await ref.read(syncControllerProvider.notifier).createInvite(role);
      if (!context.mounted) return;
      await showDialog<void>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: Text(l10n.inviteCodeTitle),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SelectableText(
                code,
                key: const Key('invite.code'),
                style: const TextStyle(fontFamily: 'monospace', fontSize: 22, letterSpacing: 2),
              ),
              const SizedBox(height: 8),
              Text(l10n.inviteCodeHint),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Clipboard.setData(ClipboardData(text: code)),
              child: Text(l10n.copy),
            ),
            FilledButton(onPressed: () => Navigator.pop(ctx), child: Text(l10n.close)),
          ],
        ),
      );
    } catch (e) {
      if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l10n.serverErrorText(e))));
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final sync = ref.watch(syncControllerProvider);
    final profile = ref.watch(profileProvider).value;
    final editor = profile?.canEditSettings ?? false;
    final children = <Widget>[
      ListTile(title: Text(l10n.serverSection, style: Theme.of(context).textTheme.titleMedium)),
    ];
    if (!sync.configured) {
      children.add(ListTile(key: const Key('server.status'), subtitle: Text(l10n.serverNotConfigured)));
    } else if (!sync.connected) {
      children.add(ListTile(key: const Key('server.status'), subtitle: Text(l10n.serverNotConnected)));
      children.add(
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: editor
              ? FilledButton(
                  key: const Key('server.register'),
                  onPressed: sync.running ? null : () => _register(context, ref),
                  child: Text(l10n.registerLab),
                )
              : OutlinedButton(
                  key: const Key('server.login'),
                  onPressed: () => context.push('/login'),
                  child: Text(l10n.loginButton),
                ),
        ),
      );
    } else {
      final last = sync.lastAt;
      children.addAll([
        ListTile(
          key: const Key('server.status'),
          leading: const Icon(Icons.cloud_done, color: ZanjirColors.success),
          title: Text(l10n.serverConnected),
          subtitle: Text(
            [
              l10n.syncPending(sync.pending),
              if (last == null) l10n.syncNever else l10n.syncLastAt(last.toLocal().toString().substring(0, 16)),
              if (sync.lastReport case final r?) l10n.syncDone(r.pushed, r.pulled),
            ].join('\n'),
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              FilledButton.icon(
                key: const Key('sync.now'),
                onPressed: sync.running ? null : () => ref.read(syncControllerProvider.notifier).syncNow(),
                icon: sync.running
                    ? const SizedBox.square(dimension: 18, child: CircularProgressIndicator(strokeWidth: 2))
                    : const Icon(Icons.sync),
                label: Text(l10n.syncNow),
              ),
              if (editor)
                OutlinedButton(
                  key: const Key('server.invite'),
                  onPressed: () => _invite(context, ref),
                  child: Text(l10n.createInvite),
                ),
              TextButton(
                key: const Key('server.logout'),
                onPressed: () => ref.read(syncControllerProvider.notifier).logout(),
                child: Text(l10n.logout),
              ),
            ],
          ),
        ),
      ]);
    }
    if (sync.error case final e?) {
      children.add(
        Padding(
          padding: const EdgeInsets.all(16),
          child: Text(
            l10n.serverErrorText(e),
            key: const Key('server.error'),
            style: const TextStyle(color: ZanjirColors.danger),
          ),
        ),
      );
    }
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: children);
  }
}

class _PasswordDialog extends StatefulWidget {
  const _PasswordDialog();

  @override
  State<_PasswordDialog> createState() => _PasswordDialogState();
}

class _PasswordDialogState extends State<_PasswordDialog> {
  final _form = GlobalKey<FormState>();
  final _password = TextEditingController();
  final _repeat = TextEditingController();

  @override
  void dispose() {
    _password.dispose();
    _repeat.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return AlertDialog(
      title: Text(l10n.registerLab),
      content: Form(
        key: _form,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(l10n.registerLabHint),
            TextFormField(
              key: const Key('register.password'),
              controller: _password,
              obscureText: true,
              decoration: InputDecoration(labelText: l10n.password),
              validator: (v) => (v ?? '').length >= 10 ? null : l10n.passwordTooShort,
            ),
            TextFormField(
              key: const Key('register.repeat'),
              controller: _repeat,
              obscureText: true,
              decoration: InputDecoration(labelText: l10n.passwordRepeat),
              validator: (v) => v == _password.text ? null : l10n.passwordMismatch,
            ),
          ],
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: Text(l10n.cancel)),
        FilledButton(
          key: const Key('register.submit'),
          onPressed: () {
            if (_form.currentState!.validate()) Navigator.pop(context, _password.text);
          },
          child: Text(l10n.registerLab),
        ),
      ],
    );
  }
}
