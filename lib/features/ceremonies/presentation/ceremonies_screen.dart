import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/ceremonies/data/ceremony_providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// Ijtimoiy bosimga qarshi kartochka (SPEC 2D.8).
class PressureCard extends StatelessWidget {
  const PressureCard({required this.index, super.key});

  final int index;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final texts = [l10n.pressure1, l10n.pressure2, l10n.pressure3];
    final theme = Theme.of(context);
    return Card(
      key: const Key('pressure-card'),
      color: theme.colorScheme.secondaryContainer,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Icon(
              Icons.format_quote,
              color: theme.colorScheme.onSecondaryContainer,
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                texts[index % texts.length],
                style: theme.textTheme.bodyMedium?.copyWith(
                  fontStyle: FontStyle.italic,
                  color: theme.colorScheme.onSecondaryContainer,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Marosim rejalari (SPEC 2D.8).
class CeremoniesScreen extends ConsumerWidget {
  const CeremoniesScreen({super.key});

  Future<void> _create(BuildContext context, WidgetRef ref) async {
    final l10n = context.l10n;
    final router = GoRouter.of(context);
    final draft = await showDialog<(String, CeremonyType, LocalDate?)>(
      context: context,
      builder: (_) => const _NewCeremonyDialog(),
    );
    if (draft == null) return;
    try {
      final plan = await (await ref.read(ceremonyServiceProvider.future))
          .create(
            title: draft.$1,
            type: draft.$2,
            eventDate: draft.$3,
            firstScenarioName: l10n.ceremonyFirstScenario,
          );
      ref.invalidate(ceremonyPlansProvider);
      await router.push(AppRoutes.ceremony(plan.meta.id));
      ref.invalidate(ceremonyPlansProvider);
    } on Object {
      AppLog.event('ceremony_create_failed');
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final plans = ref.watch(ceremonyPlansProvider);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.ceremoniesTitle)),
      floatingActionButton: FloatingActionButton.extended(
        key: const Key('ceremony-add'),
        icon: const Icon(Icons.add),
        label: Text(l10n.ceremonyAdd),
        onPressed: () => _create(context, ref),
      ),
      body: switch (plans) {
        AsyncData(:final value) => ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 96),
          children: [
            Text(l10n.ceremoniesHint),
            const SizedBox(height: 8),
            const PressureCard(index: 0),
            const SizedBox(height: 8),
            if (value.isEmpty)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 12),
                child: Text(l10n.ceremoniesEmpty),
              ),
            for (final p in value)
              Card(
                key: Key('ceremony-${p.meta.id}'),
                child: ListTile(
                  leading: const Icon(Icons.event_note_outlined),
                  title: Text(p.title),
                  subtitle: Text(
                    [
                      l10n.ceremonyType(p.type),
                      l10n.ceremonyStatus(p.status),
                      if (p.eventDate != null) formatDate(p.eventDate!),
                    ].join(' · '),
                  ),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () async {
                    await context.push(AppRoutes.ceremony(p.meta.id));
                    ref.invalidate(ceremonyPlansProvider);
                  },
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

class _NewCeremonyDialog extends StatefulWidget {
  const _NewCeremonyDialog();

  @override
  State<_NewCeremonyDialog> createState() => _NewCeremonyDialogState();
}

class _NewCeremonyDialogState extends State<_NewCeremonyDialog> {
  final _name = TextEditingController();
  CeremonyType _type = CeremonyType.toy;
  LocalDate? _date;

  @override
  void dispose() {
    _name.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return AlertDialog(
      title: Text(l10n.ceremonyAdd),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextField(
              key: const Key('ceremony-name'),
              controller: _name,
              autofocus: true,
              decoration: InputDecoration(labelText: l10n.ceremonyNameLabel),
              onChanged: (_) => setState(() {}),
            ),
            const SizedBox(height: 12),
            Text(l10n.ceremonyTypeTitle),
            Wrap(
              spacing: 8,
              children: [
                for (final t in CeremonyType.values)
                  ChoiceChip(
                    key: Key('ceremony-type-${t.name}'),
                    label: Text(l10n.ceremonyType(t)),
                    selected: _type == t,
                    onSelected: (_) => setState(() => _type = t),
                  ),
              ],
            ),
            const SizedBox(height: 8),
            OutlinedButton(
              key: const Key('ceremony-date'),
              onPressed: () async {
                final now = DateTime.now();
                final picked = await showDatePicker(
                  context: context,
                  firstDate: DateTime(now.year - 1),
                  lastDate: DateTime(now.year + 10),
                  initialDate: now,
                );
                if (picked != null) {
                  setState(() => _date = LocalDate.fromDateTime(picked));
                }
              },
              child: Text(
                _date == null
                    ? l10n.ceremonyDateNone
                    : l10n.ceremonyDate(formatDate(_date!)),
              ),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text(l10n.cancel),
        ),
        FilledButton(
          key: const Key('ceremony-save'),
          onPressed: _name.text.trim().isEmpty
              ? null
              : () => Navigator.pop(context, (_name.text.trim(), _type, _date)),
          child: Text(l10n.save),
        ),
      ],
    );
  }
}
