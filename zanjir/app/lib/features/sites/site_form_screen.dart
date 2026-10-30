import 'package:drift/drift.dart' show Value;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:zanjir_core/zanjir_core.dart';

import '../../core/numbers.dart';
import '../../core/providers.dart';
import '../../l10n/gen/app_localizations.dart';
import '../../l10n/labels.dart';
import '../../widgets/number_field.dart';

/// Obyekt yaratish yoki tahrirlash (`siteId != null`).
class SiteFormScreen extends ConsumerStatefulWidget {
  const SiteFormScreen({super.key, this.siteId});
  final String? siteId;

  @override
  ConsumerState<SiteFormScreen> createState() => _SiteFormScreenState();
}

class _SiteFormScreenState extends ConsumerState<SiteFormScreen> {
  final _form = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _address = TextEditingController();
  final _customer = TextEditingController();
  final _u0 = TextEditingController();
  EarthingSystem? _earthing;
  bool _loaded = false;

  @override
  void initState() {
    super.initState();
    final id = widget.siteId;
    if (id == null) {
      _loaded = true;
      _u0.text = '220';
    } else {
      ref.read(siteProvider(id).future).then((s) {
        if (s == null || !mounted) return;
        setState(() {
          _name.text = s.name;
          _address.text = s.address ?? '';
          _customer.text = s.customer ?? '';
          _u0.text = s.u0Volts == null ? '' : formatDecimal(s.u0Volts!);
          _earthing = s.earthingSystem;
          _loaded = true;
        });
      });
    }
  }

  @override
  void dispose() {
    for (final c in [_name, _address, _customer, _u0]) {
      c.dispose();
    }
    super.dispose();
  }

  String? _opt(TextEditingController c) => c.text.trim().isEmpty ? null : c.text.trim();

  Future<void> _save() async {
    if (!_form.currentState!.validate()) return;
    final l10n = AppLocalizations.of(context);
    try {
      final repos = await ref.read(repositoriesProvider.future);
      final id = widget.siteId;
      final String siteId;
      if (id == null) {
        final s = await repos.sites.create(
          name: _name.text.trim(),
          address: _opt(_address),
          customer: _opt(_customer),
          earthingSystem: _earthing,
          u0Volts: parseDecimal(_u0.text),
        );
        siteId = s.id;
      } else {
        final old = (await repos.sites.get(id))!;
        await repos.sites.update(
          old.copyWith(
            name: _name.text.trim(),
            address: Value(_opt(_address)),
            customer: Value(_opt(_customer)),
            earthingSystem: Value(_earthing),
            u0Volts: Value(parseDecimal(_u0.text)),
          ),
        );
        siteId = id;
      }
      invalidateSite(ref, siteId);
      if (mounted) id == null ? context.pushReplacement('/sites/$siteId') : context.pop();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l10n.errorText(e))));
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.siteFormTitle)),
      body: !_loaded
          ? const Center(child: CircularProgressIndicator())
          : Form(
              key: _form,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  TextFormField(
                    key: const Key('site.name'),
                    controller: _name,
                    decoration: InputDecoration(labelText: l10n.siteName),
                    validator: (v) => (v ?? '').trim().isEmpty ? l10n.requiredField : null,
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _address,
                    decoration: InputDecoration(labelText: l10n.address),
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _customer,
                    decoration: InputDecoration(labelText: l10n.customer),
                  ),
                  const SizedBox(height: 12),
                  DropdownButtonFormField<EarthingSystem?>(
                    isExpanded: true,
                    key: const Key('site.earthing'),
                    initialValue: _earthing,
                    decoration: InputDecoration(labelText: l10n.earthingSystem),
                    items: [
                      DropdownMenuItem(child: Text(l10n.notSet)),
                      for (final e in EarthingSystem.values) DropdownMenuItem(value: e, child: Text(e.code)),
                    ],
                    onChanged: (v) => setState(() => _earthing = v),
                  ),
                  const SizedBox(height: 12),
                  NumberField(controller: _u0, label: l10n.u0Volts),
                  const SizedBox(height: 16),
                  FilledButton(key: const Key('site.save'), onPressed: _save, child: Text(l10n.save)),
                ],
              ),
            ),
    );
  }
}
