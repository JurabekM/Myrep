import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/money/allocation.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/features/partnerships/domain/partnership_rules.dart';
import 'package:meta/meta.dart';

/// Taqsimotdagi sherik: roli, foyda ulushi (bp) va kiritgan kapitali.
@immutable
final class DistributionParty {
  const DistributionParty({
    required this.role,
    required this.shareBp,
    required this.capital,
  });

  final PartnerRole role;
  final int shareBp;
  final Money capital;
}

/// Davr taqsimoti natijasi (sheriklar tartibida).
@immutable
final class DistributionResult {
  const DistributionResult({
    required this.shares,
    required this.buyout,
    required this.buyoutPaid,
  });

  /// Har sherikning yakuniy ulushi (manfiy — zarar ulushi), buyout bilan.
  final List<Money> shares;

  /// Buyout harakati: mehnat egasidan ayirilgan (manfiy), kapital egasiga
  /// qo'shilgan (musbat). Foyda bo'lmasa — nollar.
  final List<Money> buyout;

  /// Shu davrda to'langan buyout (kapital egasi ulushini sotib olish).
  final Money buyoutPaid;
}

/// Davr oxirida foyda yoki zararni taqsimlash (SPEC 2E.1, 2E.3):
///
/// * **foyda** — kelishilgan ulushlar bo'yicha (`allocate`, largest
///   remainder); kamayib boruvchi musharakada mehnat egasi ulushidan
///   [buyoutDue] (ko'pi bilan [buyoutRemaining] va o'z ulushi) ayiriladi va
///   kapital egasi(lar)iga (kapitaliga mutanosib) qo'shiladi;
/// * **zarar** — `PartnershipRules.lossShares`: musharaka — kapitalga
///   mutanosib, mudaraba — kapital egasida (beparvolik — izoh bilan
///   ishchiga). Zararda buyout yo'q.
DistributionResult distribute({
  required PartnershipType type,
  required List<DistributionParty> parties,
  required Money net,
  Money? buyoutDue,
  Money? buyoutRemaining,
  bool negligence = false,
  String? note,
}) {
  final c = net.currency;
  final zero = Money.zero(c);
  final n = parties.length;
  final noBuyout = List.filled(n, zero);
  if (net.isZero) {
    return DistributionResult(
      shares: List.filled(n, zero),
      buyout: noBuyout,
      buyoutPaid: zero,
    );
  }
  if (net.isNegative) {
    final losses = PartnershipRules.lossShares(
      type: type,
      roles: [for (final p in parties) p.role],
      capital: [for (final p in parties) p.capital],
      loss: -net,
      negligence: negligence,
      note: note,
    );
    return DistributionResult(
      shares: [for (final l in losses) -l],
      buyout: noBuyout,
      buyoutPaid: zero,
    );
  }
  final shares = allocate(net, [for (final p in parties) p.shareBp]);
  final buyers = [
    for (var i = 0; i < n; i++)
      if (parties[i].role == PartnerRole.worker) i,
  ];
  final sellers = [
    for (var i = 0; i < n; i++)
      if (parties[i].role == PartnerRole.capitalProvider) i,
  ];
  var due = buyoutDue ?? zero;
  if (buyoutRemaining != null && due > buyoutRemaining) due = buyoutRemaining;
  final buyerShare = Money.sum([for (final i in buyers) shares[i]], c);
  if (due > buyerShare) due = buyerShare;
  if (!due.isPositive || buyers.isEmpty || sellers.isEmpty) {
    return DistributionResult(
      shares: shares,
      buyout: noBuyout,
      buyoutPaid: zero,
    );
  }
  final moves = List.filled(n, zero);
  // Mehnat egalaridan — ulushiga mutanosib.
  final paid = allocate(due, [for (final i in buyers) shares[i].minorUnits]);
  for (final (k, i) in buyers.indexed) {
    moves[i] = -paid[k];
  }
  // Kapital egalariga — kapitaliga mutanosib.
  final weights = [for (final i in sellers) parties[i].capital.minorUnits];
  final got = allocate(
    due,
    weights.every((w) => w == 0) ? List.filled(weights.length, 1) : weights,
  );
  for (final (k, i) in sellers.indexed) {
    moves[i] = got[k];
  }
  return DistributionResult(
    shares: [for (var i = 0; i < n; i++) shares[i] + moves[i]],
    buyout: moves,
    buyoutPaid: due,
  );
}
