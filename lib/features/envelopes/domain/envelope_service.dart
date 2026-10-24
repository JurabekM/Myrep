import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/budget/domain/rescue.dart';
import 'package:baraka_daftari/features/envelopes/domain/envelope.dart';
import 'package:baraka_daftari/features/expenses/domain/expense.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';
import 'package:meta/meta.dart';

/// Konvertning joriy holati.
@immutable
final class EnvelopeStatus {
  const EnvelopeStatus({
    required this.envelope,
    required this.week,
    required this.current,
    required this.pendingClose,
  });

  final Envelope envelope;
  final DateRange week;
  final EnvelopeWeek current;

  /// Naqd konvertning o'tgan, qoldig'i hali kiritilmagan haftalari.
  final List<EnvelopePeriod> pendingClose;
}

/// Haftalik konvertlar (SPEC 2B.6). Hafta — uy xo'jaligi taqvimi bo'yicha
/// (juma). Kategoriyaga bog'langan har xarajat (naqd ham, karta ham)
/// konvertdan ayiriladi.
class EnvelopeService {
  EnvelopeService({
    required HouseholdRepository households,
    required EnvelopeRepository envelopes,
    required EnvelopePeriodRepository periods,
    required ExpenseRepository expenses,
    required SavingsRescueRepository rescues,
    required SyncMetaFactory metaFactory,
    required Clock clock,
  }) : _households = households,
       _envelopes = envelopes,
       _periods = periods,
       _expenses = expenses,
       _rescues = rescues,
       _meta = metaFactory,
       _clock = clock;

  static const errTitleRequired = 'envelope_title_required';
  static const errNotPositive = 'envelope_limit_must_be_positive';
  static const errAlreadyClosed = 'envelope_period_closed';
  static const errNegativeLeftover = 'envelope_leftover_negative';

  final HouseholdRepository _households;
  final EnvelopeRepository _envelopes;
  final EnvelopePeriodRepository _periods;
  final ExpenseRepository _expenses;
  final SavingsRescueRepository _rescues;
  final SyncMetaFactory _meta;
  final Clock _clock;

  LocalDate get _today => Tashkent.dateOf(_clock.nowUtc());

  Future<List<Envelope>> envelopes() async => [
    for (final e in await _envelopes.listActive(
      (await _households.current()).meta.id,
    ))
      if (!e.isArchived) e,
  ];

  /// Yangi konvert. Kategoriya bitta konvertga tegishli bo'ladi — boshqa
  /// konvertlardan olib tashlanadi.
  Future<Envelope> create({
    required String title,
    required Money weeklyLimit,
    bool isCash = true,
    List<String> categoryIds = const [],
  }) async {
    if (title.trim().isEmpty) throw const DomainRuleException(errTitleRequired);
    if (!weeklyLimit.isPositive) {
      throw const DomainRuleException(errNotPositive);
    }
    for (final other in await envelopes()) {
      final rest = [
        for (final id in other.categoryIds)
          if (!categoryIds.contains(id)) id,
      ];
      if (rest.length != other.categoryIds.length) {
        await _envelopes.update(other.copyWith(categoryIds: rest));
      }
    }
    final hh = (await _households.current()).meta.id;
    return _envelopes.add(
      Envelope(
        meta: _meta.create(hh),
        title: title.trim(),
        weeklyLimit: weeklyLimit,
        isCash: isCash,
        categoryIds: categoryIds,
      ),
    );
  }

  Future<void> archive(Envelope e) async {
    await _envelopes.update(e.copyWith(isArchived: true));
  }

  Future<Money> _spent(Envelope e, DateRange week) async {
    var spent = Money.zero(e.weeklyLimit.currency);
    for (final x in await _expenses.listInRange(
      e.meta.householdId,
      week,
    )) {
      if (e.categoryIds.contains(x.categoryId) &&
          x.amount.currency == spent.currency) {
        spent += x.amount;
      }
    }
    return spent;
  }

  /// Holat: joriy hafta davri yaratiladi (limit surati); o'tgan haftalar
  /// yopiladi — karta konvertida avtomatik (hisobdagi qoldiq), naqdda
  /// foydalanuvchi qoldiqni kiritguncha kutadi.
  Future<List<EnvelopeStatus>> status() async {
    final h = await _households.current();
    final week = h.calendar.weekOf(_today);
    final out = <EnvelopeStatus>[];
    for (final e in await envelopes()) {
      final periods = await _periods.forEnvelope(e.meta.id);
      final pending = <EnvelopePeriod>[];
      for (final p in periods) {
        if (p.isClosed || !p.weekStart.isBefore(week.start)) continue;
        if (e.isCash) {
          pending.add(p);
        } else {
          final pw = DateRange(p.weekStart, p.weekStart.plusDays(7));
          await _close(
            p,
            EnvelopeWeek(
              limit: p.limit,
              spent: await _spent(e, pw),
            ).computedLeftover,
          );
        }
      }
      var current = periods.where((p) => p.weekStart == week.start).firstOrNull;
      current ??= await _periods.add(
        EnvelopePeriod(
          meta: _meta.create(h.meta.id),
          envelopeId: e.meta.id,
          weekStart: week.start,
          limit: e.weeklyLimit,
        ),
      );
      out.add(
        EnvelopeStatus(
          envelope: e,
          week: week,
          current: EnvelopeWeek(
            limit: current.limit,
            spent: await _spent(e, week),
          ),
          pendingClose: pending,
        ),
      );
    }
    return out;
  }

  /// Naqd konvert haftasini yopish: haqiqatda qolgan naqd kiritiladi.
  Future<EnvelopePeriod> closeWithLeftover(
    EnvelopePeriod p,
    Money leftover,
  ) async {
    if (p.isClosed) throw const DomainRuleException(errAlreadyClosed);
    if (leftover.isNegative) {
      throw const DomainRuleException(errNegativeLeftover);
    }
    return _close(p, leftover);
  }

  Future<EnvelopePeriod> _close(EnvelopePeriod p, Money leftover) async {
    final closed = await _periods.update(
      p.copyWith(leftover: leftover, closedAt: _clock.nowUtc()),
    );
    if (leftover.isPositive) {
      await _rescues.add(
        SavingsRescue(
          meta: _meta.create(p.meta.householdId),
          kind: RescueKind.envelopeLeftover,
          amount: leftover,
          // Qoldiq hafta tugaganda «qutqariladi» — keyingi haftaning
          // birinchi kuni.
          occurredOn: p.weekStart.plusDays(7),
          sourceId: p.meta.id,
        ),
      );
    }
    return closed;
  }
}
