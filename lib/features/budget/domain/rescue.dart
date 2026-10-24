import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/repository.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:freezed_annotation/freezed_annotation.dart';

part 'rescue.freezed.dart';

/// «Qutqarilgan pul» yozuvi (SPEC 2B.7).
@freezed
abstract class SavingsRescue with _$SavingsRescue implements Synced {
  const factory SavingsRescue({
    required SyncMeta meta,
    required RescueKind kind,

    /// Obuna uchun — oylik ekvivalent; konvert uchun — qoldiq;
    /// o'tkazish uchun — o'tkazilgan summa.
    required Money amount,
    required LocalDate occurredOn,
    String? sourceId,
  }) = _SavingsRescue;
}

abstract interface class SavingsRescueRepository
    implements SyncedRepository<SavingsRescue> {}

/// Qutqarilgan pul hisobining tarkibi (bitta davr uchun).
@immutable
final class RescueBreakdown {
  const RescueBreakdown({
    required this.havasDelta,
    required this.subscriptions,
    required this.envelopes,
    required this.transferred,
    required this.hasBaseline,
  });

  /// Bazaviy davrga nisbatan havas kamayishi; manfiy — ko'proq sarflangan.
  final Money havasDelta;
  final Money subscriptions;
  final Money envelopes;

  /// Shu davrda «Kelajagim»ga o'tkazilgani.
  final Money transferred;
  final bool hasBaseline;

  bool get spentMore => havasDelta.isNegative;

  /// Ko'rsatiladigan havas qismi — manfiy bo'lsa 0 (ayblanmaydi).
  Money get havasShown => _nonNegative(havasDelta);

  Money get total => havasShown + subscriptions + envelopes;

  /// Hali o'tkazilmagan qismi.
  Money get available => _nonNegative(total - transferred);

  static Money _nonNegative(Money m) =>
      m.isNegative ? Money.zero(m.currency) : m;
}

/// «Qutqarilgan pul» formulasi (SPEC 2B.7, MVP_PLAN Vazifa 8):
///
/// * havas kamayishi = bazaviy davr havasi × (joriy davrning o'tgan kunlari
///   / bazaviy davr kunlari) − joriy davr havasi (manfiy bo'lishi mumkin —
///   ko'rsatishda 0);
/// * + bekor qilingan obunalar tejami ([subscriptionSavings]);
/// * + shu davrda yopilgan konvert qoldiqlari.
///
/// Joriy davr hali tugamagan bo'lsa faqat o'tgan kunlar olinadi — hafta
/// boshida «katta qutqarish» ko'rinmasin.
RescueBreakdown computeRescue({
  required CurrencyCode currency,
  required int elapsedDays,
  required Money currentHavas,
  required Money subscriptions,
  required Money envelopeLeftovers,
  required Money transferred,
  Money? baselineHavas,
  int baselineDays = 30,
}) {
  if (elapsedDays <= 0) throw ArgumentError.value(elapsedDays, 'elapsedDays');
  if (baselineDays <= 0) {
    throw ArgumentError.value(baselineDays, 'baselineDays');
  }
  final delta = baselineHavas == null
      ? Money.zero(currency)
      : baselineHavas
                .scaled(elapsedDays, baselineDays)
                .roundTo(currency.minorPerMajor) -
            currentHavas;
  return RescueBreakdown(
    havasDelta: delta,
    subscriptions: subscriptions,
    envelopes: envelopeLeftovers,
    transferred: transferred,
    hasBaseline: baselineHavas != null,
  );
}

/// Bekor qilingan obunalar tejami davrda: har biri bekor qilingan kundan
/// (davr boshidan oldin bo'lsa — davr boshidan) [today] gacha, oylik
/// ekvivalent × kunlar / 30. Butun birlikkacha yaxlitlanadi.
Money subscriptionSavings({
  required CurrencyCode currency,
  required Iterable<(Money monthly, LocalDate cancelledOn)> cancelled,
  required DateRange period,
  required LocalDate today,
}) {
  var total = Money.zero(currency);
  for (final (monthly, on) in cancelled) {
    if (monthly.currency != currency) continue;
    final from = on.isAfter(period.start) ? on : period.start;
    final days = from.daysUntil(today) + 1;
    if (days <= 0 || !from.isBefore(period.endExclusive)) continue;
    total += monthly.scaled(days, 30);
  }
  return total.roundTo(currency.minorPerMajor);
}
