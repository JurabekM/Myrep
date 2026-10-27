import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/allocation.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:meta/meta.dart';

/// Foyda sharti kiritmasi (SPEC 2E.1): faqat **sof foydaning foizi**.
/// Qat'iy summa yoki kafolatlangan daromad — sheriklik emas (ribo yoki
/// qarz); bunday kiritma domen darajasida rad etiladi.
@immutable
final class ProfitShareInput {
  const ProfitShareInput.percent(int this.basisPoints)
    : fixedAmount = null,
      guaranteed = false;

  /// Urinish: kapital egasiga qat'iy summa (masalan, «oyiga 2 mln»).
  const ProfitShareInput.fixed(Money this.fixedAmount)
    : basisPoints = null,
      guaranteed = false;

  /// Urinish: «zarar bo'lsa ham shuncha foyda kafolatlanadi».
  const ProfitShareInput.guaranteed(this.basisPoints)
    : fixedAmount = null,
      guaranteed = true;

  final int? basisPoints;
  final Money? fixedAmount;
  final bool guaranteed;
}

/// Kapital bandi: pul yoki narxlangan uskuna.
@immutable
final class CapitalItem {
  const CapitalItem({
    required this.kind,
    required this.title,
    required this.amount,
  });

  final CapitalKind kind;
  final String title;
  final Money amount;
}

/// Sherik qoralamasi (shartnoma ustasidan).
@immutable
final class PartnerDraft {
  const PartnerDraft({
    required this.name,
    required this.role,
    required this.profit,
    this.capital = const [],
    this.isMe = false,
  });

  final String name;
  final PartnerRole role;
  final ProfitShareInput profit;
  final List<CapitalItem> capital;
  final bool isMe;

  bool get providesCapital =>
      role == PartnerRole.capitalProvider || role == PartnerRole.both;
}

/// Sheriklik qoidalari (SPEC 2E.1) — kod darajasida majburiy.
abstract final class PartnershipRules {
  /// «Bu sheriklik emas — ribo yoki qarz».
  static const errNotPartnership = 'partnership_fixed_return_is_riba';
  static const errSharesTotal = 'partnership_shares_must_total_100';
  static const errShareNegative = 'partnership_share_negative';
  static const errMinPartners = 'partnership_needs_two_partners';
  static const errNameRequired = 'partnership_name_required';
  static const errNoCapital = 'partnership_no_capital';

  /// Mudarabada kapital bir tomondan, mehnat boshqa tomondan.
  static const errMudarabaRoles = 'mudaraba_needs_provider_and_worker';
  static const errMudarabaWorkerCapital = 'mudaraba_worker_has_no_capital';

  /// Musharakada har bir sherik kapital kiritadi.
  static const errMusharakaCapital = 'musharaka_each_partner_capital';

  /// Mudarabada ishchiga zarar faqat beparvolik izohi bilan.
  static const errNegligenceNote = 'mudaraba_negligence_note_required';

  static void _profit(ProfitShareInput p) {
    if (p.fixedAmount != null || p.guaranteed) {
      throw const DomainRuleException(errNotPartnership);
    }
    if (p.basisPoints == null || p.basisPoints! < 0) {
      throw const DomainRuleException(errShareNegative);
    }
  }

  static Money capitalOf(PartnerDraft p, CurrencyCode c) =>
      Money.sum(p.capital.map((x) => x.amount), c);

  /// Hamma qoidalarni tekshiradi; buzilsa — `DomainRuleException`.
  static void validate(
    PartnershipType type,
    List<PartnerDraft> partners,
    CurrencyCode currency,
  ) {
    if (partners.length < 2) throw const DomainRuleException(errMinPartners);
    for (final p in partners) {
      if (p.name.trim().isEmpty) {
        throw const DomainRuleException(errNameRequired);
      }
      _profit(p.profit);
      if (p.capital.any((x) => !x.amount.isPositive)) {
        throw const DomainRuleException(errNoCapital);
      }
    }
    final total = partners.fold(0, (s, p) => s + p.profit.basisPoints!);
    if (total != basisPointsWhole) {
      throw const DomainRuleException(errSharesTotal);
    }
    switch (type) {
      case PartnershipType.mudaraba:
        final providers = partners.where(
          (p) => p.role == PartnerRole.capitalProvider,
        );
        final workers = partners.where((p) => p.role == PartnerRole.worker);
        if (providers.isEmpty ||
            workers.isEmpty ||
            partners.any((p) => p.role == PartnerRole.both)) {
          throw const DomainRuleException(errMudarabaRoles);
        }
        if (workers.any((w) => w.capital.isNotEmpty)) {
          throw const DomainRuleException(errMudarabaWorkerCapital);
        }
        if (providers.any((p) => !capitalOf(p, currency).isPositive)) {
          throw const DomainRuleException(errNoCapital);
        }
      case PartnershipType.musharaka:
        if (partners.any((p) => !capitalOf(p, currency).isPositive)) {
          throw const DomainRuleException(errMusharakaCapital);
        }
    }
  }

  /// Zarar taqsimoti (SPEC 2E.1), [roles] va [capital] — sheriklar
  /// tartibida.
  ///
  /// * `MUSHARAKA`: `lossShare_i = capital_i / Σcapital`.
  /// * `MUDARABA`: moliyaviy zarar kapital egalarida (kapitaliga
  ///   mutanosib); ishchi faqat mehnatidan ayriladi. Istisno —
  ///   [negligence] (izohi [note] majburiy): zarar ishchi(lar)ga.
  static List<Money> lossShares({
    required PartnershipType type,
    required List<PartnerRole> roles,
    required List<Money> capital,
    required Money loss,
    bool negligence = false,
    String? note,
  }) {
    final c = loss.currency;
    final n = roles.length;
    if (!loss.isPositive) return List.filled(n, Money.zero(c));
    List<Money> spread(bool Function(int i) who, List<int> weights) {
      final idx = [
        for (var i = 0; i < n; i++)
          if (who(i)) i,
      ];
      final w = [for (final i in idx) weights[i]];
      final parts = allocate(
        loss,
        w.every((x) => x == 0) ? List.filled(w.length, 1) : w,
      );
      final out = List.filled(n, Money.zero(c));
      for (final (k, i) in idx.indexed) {
        out[i] = parts[k];
      }
      return out;
    }

    final weights = [for (final m in capital) m.minorUnits];
    switch (type) {
      case PartnershipType.musharaka:
        return spread((_) => true, weights);
      case PartnershipType.mudaraba:
        if (negligence) {
          if (note == null || note.trim().isEmpty) {
            throw const DomainRuleException(errNegligenceNote);
          }
          return spread(
            (i) => roles[i] == PartnerRole.worker,
            List.filled(n, 1),
          );
        }
        return spread((i) => roles[i] != PartnerRole.worker, weights);
    }
  }
}

/// Buyout jadvalining bir oyi.
@immutable
final class BuyoutRow {
  const BuyoutRow({
    required this.dueOn,
    required this.payment,
    required this.remaining,
    required this.providerShareBp,
  });

  final LocalDate dueOn;
  final Money payment;

  /// Shu to'lovdan keyin kapital egasining qolgan ulushi (summada).
  final Money remaining;

  /// Kapital egasining ulushi umumiy kapitalga nisbatan (bp).
  final int providerShareBp;
}

/// Kamayib boruvchi musharaka (SPEC 2E.2): mehnat egasi kapital egasining
/// [providerStake] ulushini oyiga [monthly] dan sotib oladi; [paid] —
/// allaqachon to'langani. Oxirgi to'lov qoldiqni aynan yopadi.
List<BuyoutRow> buyoutSchedule({
  required Money providerStake,
  required Money totalCapital,
  required Money monthly,
  required LocalDate firstDue,
  Money? paid,
}) {
  if (!monthly.isPositive) return const [];
  var rest = providerStake - (paid ?? Money.zero(providerStake.currency));
  final out = <BuyoutRow>[];
  var k = 0;
  while (rest.isPositive) {
    final pay = monthly > rest ? rest : monthly;
    rest -= pay;
    out.add(
      BuyoutRow(
        dueOn: firstDue.plusMonths(k),
        payment: pay,
        remaining: rest,
        providerShareBp: ratioBasisPoints(rest, totalCapital) ?? 0,
      ),
    );
    k++;
  }
  return out;
}
