import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/features/household/data/household_providers.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'member_views.g.dart';

/// Oila a'zolari (egasi birinchi; yo'q bo'lsa avtomatik yaratiladi —
/// ismi bo'sh, ekranda «Men» deb ko'rinadi).
@riverpod
Future<List<Member>> members(Ref ref) async =>
    (await ref.watch(householdServiceProvider.future)).members(ownerName: '');

/// «Kim?» tanlovi — faqat oilada bir nechta a'zo bo'lsa ko'rinadi.
class MemberPicker extends ConsumerWidget {
  const MemberPicker({
    required this.selectedId,
    required this.onSelected,
    super.key,
  });

  final String? selectedId;
  final ValueChanged<String> onSelected;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final list = ref.watch(membersProvider).valueOrNull ?? const [];
    if (list.length < 2) return const SizedBox.shrink();
    final l10n = context.l10n;
    final current = selectedId ?? list.first.meta.id;
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(l10n.memberLabel, style: Theme.of(context).textTheme.labelLarge),
          const SizedBox(height: 4),
          Wrap(
            spacing: 8,
            children: [
              for (final m in list)
                ChoiceChip(
                  key: Key('member-${m.meta.id}'),
                  label: Text(l10n.member(m)),
                  selected: m.meta.id == current,
                  onSelected: (_) => onSelected(m.meta.id),
                ),
            ],
          ),
        ],
      ),
    );
  }
}
