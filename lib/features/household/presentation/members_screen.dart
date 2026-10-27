import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/refresh.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/features/household/data/household_providers.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';
import 'package:baraka_daftari/features/household/presentation/member_views.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Oilaviy rejim (lokal): bir qurilmada bir nechta a'zo (SPEC 2.3).
/// A'zolar ism bosh harfi bilan ko'rsatiladi (rasm/yuz tasviri yo'q).
class MembersScreen extends ConsumerWidget {
  const MembersScreen({super.key});

  Future<void> _edit(BuildContext context, WidgetRef ref, [Member? m]) async {
    final l10n = context.l10n;
    final messenger = ScaffoldMessenger.of(context);
    final result = await showDialog<(String, bool)>(
      context: context,
      builder: (_) => _MemberDialog(member: m),
    );
    if (result == null) return;
    try {
      final service = await ref.read(householdServiceProvider.future);
      if (m == null) {
        await service.addMember(
          result.$1,
          result.$2 ? MemberRole.child : MemberRole.adult,
        );
      } else {
        await service.rename(m, result.$1);
      }
      refreshMoneyViews(ref);
    } on Object {
      AppLog.event('member_save_failed');
      messenger.showSnackBar(SnackBar(content: Text(l10n.genericError)));
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final members = ref.watch(membersProvider);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.sectionMembers)),
      floatingActionButton: FloatingActionButton.extended(
        key: const Key('member-add'),
        icon: const Icon(Icons.add),
        label: Text(l10n.memberAdd),
        onPressed: () => _edit(context, ref),
      ),
      body: switch (members) {
        AsyncError() => Center(child: Text(l10n.genericError)),
        AsyncData(:final value) => ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 96),
          children: [
            Text(l10n.membersHint),
            const SizedBox(height: 12),
            Card(
              child: Column(
                children: [
                  for (final (i, m) in value.indexed) ...[
                    if (i > 0) const Divider(height: 1),
                    ListTile(
                      key: Key('member-row-$i'),
                      leading: CircleAvatar(
                        child: Text(
                          l10n.member(m).characters.first.toUpperCase(),
                        ),
                      ),
                      title: Text(l10n.member(m)),
                      subtitle: Text(
                        [
                          if (m.isOwner) l10n.memberOwnerTag,
                          if (m.role == MemberRole.child) l10n.memberChildTag,
                        ].join(' · '),
                      ),
                      onTap: () => _edit(context, ref, m),
                      trailing: m.isOwner
                          ? null
                          : IconButton(
                              tooltip: l10n.delete,
                              icon: const Icon(Icons.delete_outline),
                              onPressed: () async {
                                await (await ref.read(
                                  householdServiceProvider.future,
                                )).remove(m);
                                refreshMoneyViews(ref);
                              },
                            ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
        _ => const Center(child: CircularProgressIndicator()),
      },
    );
  }
}

class _MemberDialog extends StatefulWidget {
  const _MemberDialog({this.member});

  final Member? member;

  @override
  State<_MemberDialog> createState() => _MemberDialogState();
}

class _MemberDialogState extends State<_MemberDialog> {
  late final _name = TextEditingController(
    text: widget.member?.displayName ?? '',
  );
  bool _child = false;

  @override
  void dispose() {
    _name.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return AlertDialog(
      title: Text(widget.member == null ? l10n.memberAdd : l10n.memberName),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          TextField(
            key: const Key('member-name'),
            controller: _name,
            autofocus: true,
            decoration: InputDecoration(labelText: l10n.memberName),
            onChanged: (_) => setState(() {}),
          ),
          if (widget.member == null)
            CheckboxListTile(
              contentPadding: EdgeInsets.zero,
              title: Text(l10n.memberIsChild),
              value: _child,
              onChanged: (v) => setState(() => _child = v ?? false),
            ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: Text(l10n.cancel),
        ),
        FilledButton(
          key: const Key('member-save'),
          onPressed: _name.text.trim().isEmpty
              ? null
              : () => Navigator.of(context).pop((_name.text, _child)),
          child: Text(l10n.save),
        ),
      ],
    );
  }
}
