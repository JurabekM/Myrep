import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/agreements/data/drift_agreement_repositories.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement.dart';
import 'package:baraka_daftari/features/agreements/domain/journal.dart';
import 'package:baraka_daftari/features/backup/domain/backup_service.dart';
import 'package:baraka_daftari/features/debts/data/drift_debt_repositories.dart';
import 'package:baraka_daftari/features/debts/domain/debt_math.dart';
import 'package:baraka_daftari/features/debts/domain/debt_service.dart';
import 'package:baraka_daftari/features/debts/domain/debts.dart';
import 'package:baraka_daftari/features/household/data/drift_household_repository.dart';
import 'package:baraka_daftari/features/household/domain/household_service.dart';
import 'package:baraka_daftari/features/income/data/drift_income_repository.dart';
import 'package:baraka_daftari/features/income/domain/income_service.dart';
import 'package:baraka_daftari/features/obligations/data/drift_obligation_repository.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../helpers/db.dart';
import '../../helpers/fake_backup_cipher.dart';

Money som(int major) => Money.major(major, CurrencyCode.uzs);

Matcher rule(String code) => throwsA(
  isA<DomainRuleException>().having((e) => e.code, 'code', code),
);

/// Bir nechta bo'limdan ma'lumot: a'zolar, daromad, qarz (jadval va
/// to'lov), imzo (BLOB).
Future<void> seed(TestDb t) async {
  final hh = DriftHouseholdRepository(t.db, t.clock);
  final members = DriftMemberRepository(t.db, t.clock);
  final households = HouseholdService(
    households: hh,
    members: members,
    metaFactory: t.meta,
  );
  await households.members(ownerName: 'Men');
  await households.addMember('Zuhra', MemberRole.adult);
  await households.completeOnboarding(
    incomeKind: IncomeKind.dailyCash,
    at: t.clock.nowUtc(),
  );
  final incomeRepo = DriftIncomeRepository(t.db, t.clock);
  await IncomeService(
    households: hh,
    incomes: incomeRepo,
    metaFactory: t.meta,
    clock: t.clock,
  ).add(
    amount: som(450000),
    source: IncomeSource.dailyWork,
    channel: PaymentChannel.cash,
  );
  final debts = DebtService(
    households: hh,
    debts: DriftDebtRepository(t.db, t.clock),
    installments: DriftDebtInstallmentRepository(t.db, t.clock),
    payments: DriftDebtPaymentRepository(t.db, t.clock),
    receivables: DriftReceivableRepository(t.db, t.clock),
    goals: DriftGoalRepository(t.db, t.clock),
    contributors: DriftDebtContributorRepository(t.db, t.clock),
    sellables: DriftSellableItemRepository(t.db, t.clock),
    incomes: incomeRepo,
    metaFactory: t.meta,
    clock: t.clock,
  );
  final v = await debts.add(
    creditorType: CreditorType.bank,
    creditorName: 'Avtokredit',
    principal: som(10000000),
    scheduleType: DebtScheduleType.annuity,
    termMonths: 12,
    annualRateBp: 2400,
  );
  await debts.pay(v.debt, v.plan.first.amount + som(500000));
  await debts.add(
    creditorType: CreditorType.relative,
    creditorName: 'Togʻam',
    principal: som(1000000),
    scheduleType: DebtScheduleType.manual,
    manual: [
      Installment(
        dueOn: LocalDate(2026, 12, 1),
        amount: som(1000000),
        interest: som(0),
      ),
    ],
  );
  // Kelishuv va append-only jurnal (trigger bilan himoyalangan).
  final journal = DriftJournalRepository(t.db, t.meta);
  final agreements = DriftAgreementRepository(t.db, t.clock);
  final ag = await agreements.add(
    Agreement(
      meta: t.meta.create(await t.householdId()),
      type: AgreementType.rent,
      title: 'Ijara',
      effectiveFrom: LocalDate(2026, 9, 1),
    ),
  );
  await DriftAgreementVersionRepository(t.db, t.clock).add(
    AgreementVersion(
      meta: t.meta.create(await t.householdId()),
      agreementId: ag.meta.id,
      version: 1,
      answers: const AgreementAnswers(
        parties: [AgreementParty(id: 'p1', name: 'A')],
      ),
    ),
  );
  await journal.append(
    ag.meta.id,
    JournalDraft(
      kind: JournalKind.openingBalance,
      date: LocalDate(2026, 9, 1),
      amount: som(1000000),
    ),
  );
  await DriftLoanSignerRepository(t.db, t.clock).add(
    LoanSigner(
      meta: t.meta.create(await t.householdId()),
      documentId: v.debt.meta.id,
      role: SignerRole.witness,
      name: 'Shoʼba',
      signaturePng: [0, 1, 2, 255, 128],
      signedAt: t.clock.nowUtc(),
    ),
  );
}

void main() {
  test('eksport → oʻchirish → import: maʼlumotlar 1:1 tiklanadi', () async {
    final source = TestDb.open();
    await seed(source);
    final before = await BackupService(
      source.db,
      FakeCipher(),
      source.clock,
    ).dump();
    expect(before['debts'], hasLength(2));
    expect(before['loan_signers']!.single['signature_png'], [
      0,
      1,
      2,
      255,
      128,
    ]);

    final file = await BackupService(
      source.db,
      FakeCipher(),
      source.clock,
    ).export('maxfiy-parol');
    expect(
      utf8.decode(file, allowMalformed: true),
      isNot(contains('Avtokredit')),
    );

    // «O'chirish»: ilova qayta o'rnatildi — yangi baza, o'z standart
    // ma'lumotlari bilan.
    final fresh = TestDb.open();
    final restore = BackupService(fresh.db, FakeCipher(), fresh.clock);
    expect((await restore.dump())['debts'], isEmpty);
    final rows = await restore.import(file, 'maxfiy-parol');

    final after = await restore.dump();
    expect(after.keys, before.keys);
    for (final table in before.keys) {
      expect(after[table], before[table], reason: table);
    }
    expect(
      rows,
      before.values.fold<int>(0, (s, rows) => s + rows.length),
    );
    // Jurnal tiklandi va zanjir butun; trigger yana faol.
    final restoredJournal = await DriftJournalRepository(
      fresh.db,
      fresh.meta,
    ).forAgreement((await fresh.db.select(fresh.db.agreements).getSingle()).id);
    expect(verifyChain(restoredJournal), isNull);
    await expectLater(
      fresh.db.customStatement('DELETE FROM journal_entries'),
      throwsA(anything),
    );
    // Tiklangan bazada servislar ishlaydi.
    final hh = await DriftHouseholdRepository(fresh.db, fresh.clock).current();
    expect(hh.incomeKind, IncomeKind.dailyCash);
    expect(hh.onboardedAt, isNotNull);
  });

  test('notoʻgʻri parol, buzilgan fayl, qisqa parol', () async {
    final t = TestDb.open();
    await seed(t);
    final s = BackupService(t.db, FakeCipher(), t.clock);
    await expectLater(s.export('qisqa'), rule(BackupService.errWeakPassword));
    final file = await s.export('maxfiy-parol');
    await expectLater(
      s.import(file, 'boshqa-parol'),
      rule(BackupService.errBadPassword),
    );
    final junk = await FakeCipher().encrypt(
      'maxfiy-parol',
      Uint8List.fromList([1, 2, 3]),
    );
    await expectLater(
      s.import(junk, 'maxfiy-parol'),
      rule(BackupService.errFormat),
    );
    // Xatodan keyin ham asl ma'lumotlar joyida.
    expect((await s.dump())['debts'], hasLength(2));
  });

  test('uy xoʻjaligi yoʻq (boʻsh) yuk bazani oʻchirmaydi', () async {
    final t = TestDb.open();
    await seed(t);
    final s = BackupService(t.db, FakeCipher(), t.clock);
    final json = jsonEncode({
      'format': BackupService.format,
      'schemaVersion': t.db.schemaVersion,
      'tables': <String, Object>{},
    });
    final empty = await FakeCipher().encrypt(
      'maxfiy-parol',
      Uint8List.fromList(gzip.encode(utf8.encode(json))),
    );
    await expectLater(
      s.import(empty, 'maxfiy-parol'),
      rule(BackupService.errFormat),
    );
    // Rad etilgandan keyin ma'lumot joyida (oldin butun baza o'chib ketardi).
    expect((await s.dump())['debts'], hasLength(2));
    expect((await s.dump())['households'], isNotEmpty);
  });

  test('boshqa sxema versiyasidagi nusxa qabul qilinmaydi', () async {
    final t = TestDb.open();
    final s = BackupService(t.db, FakeCipher(), t.clock);
    final json = jsonEncode({
      'format': BackupService.format,
      'schemaVersion': t.db.schemaVersion + 1,
      'tables': <String, Object>{},
    });
    final file = await FakeCipher().encrypt(
      'maxfiy-parol',
      Uint8List.fromList(gzip.encode(utf8.encode(json))),
    );
    await expectLater(
      s.import(file, 'maxfiy-parol'),
      rule(BackupService.errVersion),
    );
  });
}
