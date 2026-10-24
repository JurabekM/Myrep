import 'package:baraka_daftari/core/domain/repository.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:freezed_annotation/freezed_annotation.dart';

part 'envelope.freezed.dart';

/// Haftalik konvert (SPEC 2B.6).
@freezed
abstract class Envelope with _$Envelope implements Synced {
  const factory Envelope({
    required SyncMeta meta,
    required String title,
    required Money weeklyLimit,
    @Default(true) bool isCash,

    /// Shu kategoriyalardagi xarajat (naqd ham, karta ham) konvertdan.
    @Default(<String>[]) List<String> categoryIds,
    @Default(false) bool isArchived,
  }) = _Envelope;
}

/// Konvertning bir haftasi.
@freezed
abstract class EnvelopePeriod with _$EnvelopePeriod implements Synced {
  const factory EnvelopePeriod({
    required SyncMeta meta,
    required String envelopeId,
    required LocalDate weekStart,

    /// Hafta boshidagi limit surati (keyin limit o'zgarsa ham shu).
    required Money limit,

    /// Yopilganda qolgan pul.
    Money? leftover,

    /// UTC; `null` — hali yopilmagan.
    DateTime? closedAt,
  }) = _EnvelopePeriod;

  const EnvelopePeriod._();

  bool get isClosed => closedAt != null;
}

/// Konvert haftasining holati (sof hisob).
@immutable
final class EnvelopeWeek {
  const EnvelopeWeek({required this.limit, required this.spent});

  final Money limit;
  final Money spent;

  Money get left => limit - spent;
  bool get isOver => spent > limit;

  /// Hisob bo'yicha qoldiq (manfiy bo'lmaydi).
  Money get computedLeftover =>
      left.isNegative ? Money.zero(limit.currency) : left;
}

abstract interface class EnvelopeRepository
    implements SyncedRepository<Envelope> {}

abstract interface class EnvelopePeriodRepository
    implements SyncedRepository<EnvelopePeriod> {
  Future<List<EnvelopePeriod>> forEnvelope(String envelopeId);
}
