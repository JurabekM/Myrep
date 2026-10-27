import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';

/// Oilaviy rejim (lokal, SPEC 2.3) va uy xo'jaligi sozlamalari.
class HouseholdService {
  HouseholdService({
    required HouseholdRepository households,
    required MemberRepository members,
    required SyncMetaFactory metaFactory,
  }) : _households = households,
       _members = members,
       _meta = metaFactory;

  static const errNameRequired = 'member_name_required';
  static const errOwnerUndeletable = 'member_owner_undeletable';
  static const errInvalidDay = 'household_invalid_month_day';

  final HouseholdRepository _households;
  final MemberRepository _members;
  final SyncMetaFactory _meta;

  Future<Household> household() => _households.current();

  /// Oylik kuni: oylik davr shu kundan boshlanadi (1–31).
  Future<Household> setMonthStartDay(int day) async {
    if (day < 1 || day > 31) throw const DomainRuleException(errInvalidDay);
    final h = await _households.current();
    return _households.update(h.copyWith(monthStartDay: day));
  }

  /// Daromad turi (bosh ekran va eslatmalar shunga moslashadi).
  Future<Household> setIncomeKind(IncomeKind kind) async {
    final h = await _households.current();
    return _households.update(h.copyWith(incomeKind: kind));
  }

  /// Onboarding yakuni (MVP_PLAN Vazifa 15): daromad turi va vaqt.
  Future<Household> completeOnboarding({
    required IncomeKind incomeKind,
    required DateTime at,
  }) async {
    final h = await _households.current();
    return _households.update(
      h.copyWith(incomeKind: incomeKind, onboardedAt: at.toUtc()),
    );
  }

  /// A'zolar (egasi birinchi). Hech kim bo'lmasa — egasi yaratiladi
  /// ([ownerName] — ARB'dan, masalan «Men»).
  Future<List<Member>> members({required String ownerName}) async {
    final hh = (await _households.current()).meta.id;
    final list = await _members.listActive(hh);
    if (list.isNotEmpty) return list;
    await _members.add(
      Member(meta: _meta.create(hh), displayName: ownerName, isOwner: true),
    );
    return _members.listActive(hh);
  }

  Future<Member> addMember(String name, MemberRole role) async {
    if (name.trim().isEmpty) throw const DomainRuleException(errNameRequired);
    final hh = (await _households.current()).meta.id;
    return _members.add(
      Member(meta: _meta.create(hh), displayName: name.trim(), role: role),
    );
  }

  Future<Member> rename(Member m, String name) {
    if (name.trim().isEmpty) throw const DomainRuleException(errNameRequired);
    return _members.update(m.copyWith(displayName: name.trim()));
  }

  Future<void> remove(Member m) {
    if (m.isOwner) throw const DomainRuleException(errOwnerUndeletable);
    return _members.softDelete(m.meta.id);
  }
}
