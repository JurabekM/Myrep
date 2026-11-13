import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/numbers.dart';
import '../../core/providers.dart';
import '../../l10n/gen/app_localizations.dart';
import '../../l10n/labels.dart';

class InstrumentFormScreen extends ConsumerStatefulWidget {
  const InstrumentFormScreen({super.key});

  @override
  ConsumerState<InstrumentFormScreen> createState() => _InstrumentFormScreenState();
}

class _InstrumentFormScreenState extends ConsumerState<InstrumentFormScreen> {
  final _form = GlobalKey<FormState>();
  final _kind = TextEditingController(text: 'MULTIFUNCTION');
  final _model = TextEditingController();
  final _serial = TextEditingController();
  final _cert = TextEditingController();
  final _until = TextEditingController();

  @override
  void dispose() {
    for (final c in [_kind, _model, _serial, _cert, _until]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _save() async {
    if (!_form.currentState!.validate()) return;
    final l10n = AppLocalizations.of(context);
    try {
      final repos = await ref.read(repositoriesProvider.future);
      await repos.instruments.create(
        kind: _kind.text.trim(),
        model: _model.text.trim(),
        serialNo: _serial.text.trim(),
        verificationCertNo: _cert.text.trim().isEmpty ? null : _cert.text.trim(),
        verifiedUntil: parseIsoDate(_until.text),
      );
      ref.invalidate(instrumentsProvider);
      if (mounted) context.pop();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l10n.errorText(e))));
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    String? required(String? v) => (v ?? '').trim().isEmpty ? l10n.requiredField : null;
    return Scaffold(
      appBar: AppBar(title: Text(l10n.addInstrument)),
      body: Form(
        key: _form,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            TextFormField(
              controller: _kind,
              decoration: InputDecoration(labelText: l10n.instrumentKind),
              validator: required,
            ),
            const SizedBox(height: 12),
            TextFormField(
              key: const Key('instrument.model'),
              controller: _model,
              decoration: InputDecoration(labelText: l10n.model),
              validator: required,
            ),
            const SizedBox(height: 12),
            TextFormField(
              key: const Key('instrument.serial'),
              controller: _serial,
              decoration: InputDecoration(labelText: l10n.serialNo),
              validator: required,
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _cert,
              decoration: InputDecoration(labelText: l10n.certNo),
            ),
            const SizedBox(height: 12),
            TextFormField(
              key: const Key('instrument.until'),
              controller: _until,
              decoration: InputDecoration(labelText: l10n.verifiedUntil),
              keyboardType: TextInputType.datetime,
              validator: (v) => (v ?? '').trim().isEmpty || parseIsoDate(v) != null ? null : l10n.invalidDate,
            ),
            const SizedBox(height: 16),
            FilledButton(key: const Key('instrument.save'), onPressed: _save, child: Text(l10n.save)),
          ],
        ),
      ),
    );
  }
}
