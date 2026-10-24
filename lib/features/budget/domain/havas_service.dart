import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/security/pin/pin_service.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/budget/domain/budget.dart';
import 'package:baraka_daftari/features/budget/domain/budget_math.dart';
import 'package:baraka_daftari/features/expenses/domain/expense.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';
import 'package:baraka_daftari/features/household/domain/member_pin_service.dart';
import 'package:meta/meta.dart';

/// Chegara taklifi va unga kim rozi bo'lgani.
@immutable
final class LimitProposal {
  const LimitProposal({
    required this.limit,
    required this.consentedBy,
    required this.adults,
  });

  final HavasLimit limit;
  final Set<String> consentedBy;

  /// Rozilik berishi kerak bo'lgan kattalar.
  final List<Member> adults;

  List<Member> get waitingFor => [
    for (final m in adults)
      if (!consentedBy.contains(m.meta.id)) m,
  ];

  /// Barcha kattalar rozi bo'lgandagina faol (SPEC 2B.3).
  bool get isAgreed => adults.isNotEmpty && waitingFor.isEmpty;
}

/// Shu oy havas holati va isrof tahlili (SPEC 2B.3, 2B.8).
@immutable
final class HavasOverview {
  const HavasOverview({
    required this.period,
    required this.spent,
    required this.ostentation,
    required this.sadaqa,
    required this.gifts,
    required this.debtFundedHavas,
    this.active,
    this.pending,
  });

  final DateRange period;

  /// Havas (sovg'a va sadaqasiz).
  final Money spent;

  /// Obro' xarajatlari — alohida ko'rsatiladi.
  final Money ostentation;

  /// Sadaqa — isrof emas, alohida.
  final Money sadaqa;

  /// Sovg'a belgisi bilan havas («siz olib kelsangiz hisobga kirmaydi»).
  final Money gifts;

  /// Qarz bilan qilingan havas — qizil bayroq.
  final List<Expense> debtFundedHavas;

  /// Faol (kelishilgan) chegara.
  final LimitProposal? active;

  /// Faoldan yangiroq, hali hamma rozi bo'lmagan taklif.
  final LimitProposal? pending;

  LimitUsage? get usage => active == null
      ? null
      : LimitUsage(spent: spent, limit: active!.limit.amount);
}

/// Havas uchun oylik chegara: oilaviy kelishuv, yumshoq ogohlantirish,
/// bloklash yo'q (SPEC 2B.3).
class HavasService {
  HavasService({
    required HouseholdRepository households,
    required MemberRepository members,
    required HavasLimitRepository limits,
    required LimitConsentRepository consents,
    required MemberPinService memberPins,
    required ExpenseRepository expenses,
    required CategoryRepository categories,
    required SyncMetaFactory metaFactory,
    required Clock clock,
  }) : _households = households,
       _members = members,
       _limits = limits,
       _consents = consents,
       _memberPins = memberPins,
       _expenses = expenses,
       _categories = categories,
       _meta = metaFactory,
       _clock = clock;

  static const errNotPositive = 'havas_limit_must_be_positive';
  static const errAdultOnly = 'havas_consent_adult_only';

  final HouseholdRepository _households;
  final MemberRepository _members;
  final HavasLimitRepository _limits;
  final LimitConsentRepository _consents;
  final MemberPinService _memberPins;
  final ExpenseRepository _expenses;
  final CategoryRepository _categories;
  final SyncMetaFactory _meta;
  final Clock _clock;

  Future<List<Member>> _adults(String hh) async => [
    for (final m in await _members.listActive(hh))
      if (m.role == MemberRole.adult) m,
  ];

  Future<LimitProposal> _proposal(HavasLimit l, List<Member> adults) async =>
      LimitProposal(
        limit: l,
        consentedBy: {
          for (final c in await _consents.forLimit(l.meta.id)) c.memberId,
        },
        adults: adults,
      );

  /// Yangi chegara taklifi. Hamma kattalar rozi bo'lguncha eski kelishilgan
  /// chegara amalda qoladi.
  Future<HavasLimit> propose(Money amount, {String? proposedBy}) async {
    if (!amount.isPositive) throw const DomainRuleException(errNotPositive);
    final hh = (await _households.current()).meta.id;
    return _limits.add(
      HavasLimit(
        meta: _meta.create(hh),
        amount: amount,
        proposedBy: proposedBy,
      ),
    );
  }

  /// Taklifni bekor qilish (faqat hali kelishilmagan bo'lsa ma'noli).
  Future<void> withdraw(HavasLimit limit) => _limits.softDelete(limit.meta.id);

  /// A'zo o'z profilini tanlab tasdiqlaydi (shaxsiy PIN bo'lsa — PIN bilan).
  /// Natija: PIN tekshiruvi va shu tasdiq bilan chegara kelishildimi.
  Future<(PinCheck, bool agreed)> consent(
    HavasLimit limit,
    Member member,
    String pin,
  ) async {
    if (member.role != MemberRole.adult) {
      throw const DomainRuleException(errAdultOnly);
    }
    final check = await _memberPins.verify(member, pin);
    if (check is! PinAccepted) return (check, false);
    final hh = limit.meta.householdId;
    final before = await _proposal(limit, await _adults(hh));
    if (!before.consentedBy.contains(member.meta.id)) {
      await _consents.add(
        LimitConsent(
          meta: _meta.create(hh),
          limitId: limit.meta.id,
          memberId: member.meta.id,
        ),
      );
    }
    final after = await _proposal(limit, await _adults(hh));
    return (check, after.isAgreed && !before.isAgreed);
  }

  Future<HavasOverview> overview() async {
    final h = await _households.current();
    final hh = h.meta.id;
    final period = h.calendar.monthOf(Tashkent.dateOf(_clock.nowUtc()));
    final adults = await _adults(hh);

    LimitProposal? active;
    LimitProposal? pending;
    // Yangisi birinchi.
    for (final l in await _limits.listActive(hh)) {
      final p = await _proposal(l, adults);
      if (p.isAgreed) {
        active = p;
        break;
      }
      pending ??= p;
    }

    final categories = {
      for (final c in await _categories.listActive(hh)) c.meta.id: c,
    };
    final currency = h.baseCurrency;
    var spent = Money.zero(currency);
    var ostentation = Money.zero(currency);
    var sadaqa = Money.zero(currency);
    var gifts = Money.zero(currency);
    final debtFunded = <Expense>[];
    for (final e in await _expenses.listInRange(hh, period)) {
      if (e.amount.currency != currency) continue;
      final c = categories[e.categoryId];
      if (c?.systemKey == CategoryKey.sadaqa) sadaqa += e.amount;
      if (e.isOstentation) ostentation += e.amount;
      if (countsAsHavas(e, c)) spent += e.amount;
      if (e.isGift && effectiveNecessity(e, c) == Necessity.havas) {
        gifts += e.amount;
      }
      if (isDebtFundedHavas(e, c)) debtFunded.add(e);
    }
    return HavasOverview(
      period: period,
      spent: spent,
      ostentation: ostentation,
      sadaqa: sadaqa,
      gifts: gifts,
      debtFundedHavas: debtFunded,
      active: active,
      pending: pending,
    );
  }
}
