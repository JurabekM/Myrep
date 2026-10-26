import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:zanjir_data/zanjir_data.dart';

import '../../core/numbers.dart';
import '../../core/providers.dart';
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
          ListTile(
            title: Text(l10n.language),
            trailing: SegmentedButton<String>(
              segments: [
                ButtonSegment(value: 'uz', label: Text(l10n.languageUz)),
                ButtonSegment(value: 'ru', label: Text(l10n.languageRu)),
              ],
              selected: {locale},
              onSelectionChanged: (s) => ref.read(localeProvider.notifier).set(s.first),
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
              leading: const Icon(Icons.science),
              title: Text('${l10n.lab}: ${org.name}'),
              subtitle: Text(
                [
                  if (org.licenseNo != null) '${l10n.licenseNo}: ${org.licenseNo}',
                  if (org.licenseValidUntil != null) formatIsoDate(org.licenseValidUntil!),
                ].join(' · '),
              ),
            ),
          ),
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
