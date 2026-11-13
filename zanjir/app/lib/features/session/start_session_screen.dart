import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:zanjir_core/zanjir_core.dart';

import '../../core/numbers.dart';
import '../../core/providers.dart';
import '../../l10n/gen/app_localizations.dart';
import '../../l10n/labels.dart';
import '../../widgets/number_field.dart';

class StartSessionScreen extends ConsumerStatefulWidget {
  const StartSessionScreen({super.key, required this.siteId});
  final String siteId;

  @override
  ConsumerState<StartSessionScreen> createState() => _StartSessionScreenState();
}

class _StartSessionScreenState extends ConsumerState<StartSessionScreen> {
  final _form = GlobalKey<FormState>();
  final _temp = TextEditingController();
  final _humidity = TextEditingController();
  SessionKind _kind = SessionKind.davriy;

  @override
  void dispose() {
    _temp.dispose();
    _humidity.dispose();
    super.dispose();
  }

  Future<void> _start() async {
    if (!_form.currentState!.validate()) return;
    final l10n = AppLocalizations.of(context);
    try {
      final repos = await ref.read(repositoriesProvider.future);
      final profile = (await ref.read(profileProvider.future))!;
      final s = await repos.sessions.start(
        siteId: widget.siteId,
        kind: _kind,
        engineerId: profile.userId,
        ambientTempC: parseDecimal(_temp.text),
        humidityPct: parseDecimal(_humidity.text),
      );
      ref.invalidate(siteSessionsProvider(widget.siteId));
      if (mounted) context.pushReplacement('/sessions/${s.id}/measure');
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l10n.errorText(e))));
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.startSession)),
      body: Form(
        key: _form,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            DropdownButtonFormField<SessionKind>(
              isExpanded: true,
              initialValue: _kind,
              decoration: InputDecoration(labelText: l10n.sessionKind),
              items: [
                for (final k in SessionKind.values) DropdownMenuItem(value: k, child: Text(l10n.sessionKindName(k))),
              ],
              onChanged: (v) => setState(() => _kind = v!),
            ),
            const SizedBox(height: 12),
            NumberField(fieldKey: const Key('session.temp'), controller: _temp, label: l10n.ambientTemp),
            Padding(padding: const EdgeInsets.only(top: 4), child: Text(l10n.tempMissingHint)),
            const SizedBox(height: 12),
            NumberField(controller: _humidity, label: l10n.humidity, textInputAction: TextInputAction.done),
            const SizedBox(height: 16),
            FilledButton(key: const Key('session.start'), onPressed: _start, child: Text(l10n.start)),
          ],
        ),
      ),
    );
  }
}
