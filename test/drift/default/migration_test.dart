// Migratsiya test infratuzilmasi (SPEC 4.4: har migratsiya test bilan).
//
// Sxema oʻzgarganda:
//   1. `AppDatabase.schemaVersion` ni oshiring;
//   2. `dart run drift_dev make-migrations` — yangi snapshot
//      (`drift_schemas/default/drift_schema_vN.json`) va `generated/`
//      yordamchilari yaratiladi;
//   3. `onUpgrade` ga qadam qoʻshing va quyidagi roʻyxatga `(N-1, N)` ni
//      yozing — test eski sxemadan yangisiga oʻtishni va natija
//      snapshotga mosligini tekshiradi.
import 'package:baraka_daftari/core/db/app_database.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/ids/uuid_v7.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/agreements/data/drift_agreement_repositories.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement.dart';
import 'package:baraka_daftari/features/agreements/domain/journal.dart';
import 'package:baraka_daftari/features/partnerships/domain/contract_template.dart';
import 'package:drift/drift.dart' hide isNotNull, isNull;
import 'package:drift/native.dart';
import 'package:drift_dev/api/migrations_native.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../helpers/fakes.dart';
import 'generated/schema.dart';

AppDatabase _open(QueryExecutor executor) {
  final clock = FakeClock();
  return AppDatabase(
    executor,
    metaFactory: SyncMetaFactory(UuidV7Generator(clock: clock), clock),
  );
}

void main() {
  driftRuntimeOptions.dontWarnAboutMultipleDatabases = true;
  late SchemaVerifier verifier;

  setUpAll(() => verifier = SchemaVerifier(GeneratedHelper()));

  test('joriy sxema versiyasi uchun snapshot bor', () {
    expect(
      GeneratedHelper.versions,
      contains(_open(NativeDatabase.memory()).schemaVersion),
    );
  });

  test('yangi oʻrnatish (onCreate) snapshotga aynan mos', () async {
    final db = _open(NativeDatabase.memory());
    addTearDown(db.close);
    await db.validateDatabaseSchema();
  });

  test('v1 → v2: mavjud maʼlumot saqlanadi, yangi ustun boʻsh', () async {
    final schema = await verifier.schemaAt(1);
    const ts = "'2026-10-01T09:00:00.000Z'";
    const meta = "'h1', $ts, $ts";
    schema.rawDatabase
      ..execute(
        'INSERT INTO households (id, household_id, created_at, updated_at) '
        "VALUES ('h1', $meta)",
      )
      ..execute(
        'INSERT INTO assets (id, household_id, created_at, updated_at, type, '
        "unit, currency, acquired_at) VALUES ('a1', $meta, 'vault', 'minor', "
        "'uzs', $ts)",
      )
      ..execute(
        'INSERT INTO allocation_rules (id, household_id, created_at, '
        'updated_at, vault_asset_id, mode, basis_points, currency) '
        "VALUES ('r1', $meta, 'a1', 'progressive', 500, 'uzs')",
      );

    final db = _open(schema.newConnection());
    addTearDown(db.close);
    await verifier.migrateAndValidate(db, 2);

    final rule = await db.select(db.allocationRules).getSingle();
    expect(rule.basisPoints, 500);
    expect(rule.progressionOfferedAt, isNull);
    // onCreate ishlamadi — seed qayta qoʻshilmaydi.
    expect(await db.select(db.categories).get(), isEmpty);
  });

  test('v4 → v5: aʼzolar saqlanadi, shaxsiy PIN boʻsh', () async {
    final schema = await verifier.schemaAt(4);
    const ts = "'2026-10-01T09:00:00.000Z'";
    const meta = "'h1', $ts, $ts";
    schema.rawDatabase
      ..execute(
        'INSERT INTO households (id, household_id, created_at, updated_at) '
        "VALUES ('h1', $meta)",
      )
      ..execute(
        'INSERT INTO members (id, household_id, created_at, updated_at, '
        "display_name, role, is_owner) VALUES ('m1', $meta, 'Men', 'adult', 1)",
      );

    final db = _open(schema.newConnection());
    addTearDown(db.close);
    await verifier.migrateAndValidate(db, 5);

    final m = await db.select(db.members).getSingle();
    expect(m.displayName, 'Men');
    expect(m.isOwner, isTrue);
    expect(m.pinRecord, isNull);
  });

  test(
    'v5 → v6: standart toifa toʻldiriladi, yangi kategoriyalar qoʻshiladi',
    () async {
      final schema = await verifier.schemaAt(5);
      const ts = "'2026-10-01T09:00:00.000Z'";
      const meta = "'h1', $ts, $ts";
      schema.rawDatabase
        ..execute(
          'INSERT INTO households (id, household_id, created_at, updated_at) '
          "VALUES ('h1', $meta)",
        )
        ..execute(
          'INSERT INTO categories (id, household_id, created_at, updated_at, '
          "system_key, sort_order) VALUES ('c1', $meta, 'children', 8)",
        )
        // Foydalanuvchi oʻzi belgilagan toifa saqlanadi.
        ..execute(
          'INSERT INTO categories (id, household_id, created_at, updated_at, '
          'system_key, default_necessity) '
          "VALUES ('c2', $meta, 'phone', 'zarur')",
        )
        ..execute(
          'INSERT INTO categories (id, household_id, created_at, updated_at, '
          "system_key) VALUES ('c3', $meta, 'sadaqa')",
        );

      final db = _open(schema.newConnection());
      addTearDown(db.close);
      await verifier.migrateAndValidate(db, 6);

      final rows = {
        for (final c in await db.select(db.categories).get())
          c.systemKey: c.defaultNecessity,
      };
      expect(rows[CategoryKey.children], Necessity.kerak);
      expect(rows[CategoryKey.phone], Necessity.zarur);
      expect(rows[CategoryKey.sadaqa], isNull);
      expect(rows[CategoryKey.snacks], Necessity.havas);
      expect(rows[CategoryKey.cafe], Necessity.havas);
      // Bor kategoriyalar ikki marta qoʻshilmaydi.
      expect(
        (await db.select(db.categories).get()).where(
          (c) => c.systemKey == CategoryKey.children,
        ),
        hasLength(1),
      );
    },
  );

  test('v6 → v7: uy xoʻjaligi saqlanadi, bazaviy oy boʻsh', () async {
    final schema = await verifier.schemaAt(6);
    const ts = "'2026-10-01T09:00:00.000Z'";
    schema.rawDatabase.execute(
      'INSERT INTO households (id, household_id, created_at, updated_at, '
      "month_start_day) VALUES ('h1', 'h1', $ts, $ts, 10)",
    );
    final db = _open(schema.newConnection());
    addTearDown(db.close);
    await verifier.migrateAndValidate(db, 7);
    // Joriy (v10) klasslari keyingi ustunlarni kutadi — xom SQL bilan.
    final h = await _household(db);
    expect(h['month_start_day'], 10);
    expect(h['rescue_baseline_start'], isNull);
    expect(await db.select(db.subscriptions).get(), isEmpty);
  });

  test(
    'v7 → v8: «Kelajagim» qorovul pulga oʻtadi, balans yoʻqolmaydi',
    () async {
      final schema = await verifier.schemaAt(7);
      const ts = "'2026-10-01T09:00:00.000Z'";
      const meta = "'h1', $ts, $ts";
      schema.rawDatabase
        ..execute(
          'INSERT INTO households (id, household_id, created_at, updated_at) '
          "VALUES ('h1', $meta)",
        )
        ..execute(
          'INSERT INTO assets (id, household_id, created_at, updated_at, type, '
          "unit, currency, acquired_at) VALUES ('a1', $meta, 'vault', 'minor', "
          "'uzs', $ts)",
        )
        ..execute(
          'INSERT INTO vault_transactions (id, household_id, created_at, '
          'updated_at, vault_asset_id, type, amount_minor, currency, reason, '
          "occurred_at) VALUES ('t1', $meta, 'a1', 'deposit', 195800000, "
          "'uzs', 'incomeShare', $ts)",
        )
        ..execute(
          'INSERT INTO vault_transactions (id, household_id, created_at, '
          'updated_at, vault_asset_id, type, amount_minor, currency, reason, '
          "reason_note, occurred_at) VALUES ('t2', $meta, 'a1', 'withdraw', "
          "800000, 'uzs', 'withdrawal', 'dori', $ts)",
        );

      final db = _open(schema.newConnection());
      addTearDown(db.close);
      await verifier.migrateAndValidate(db, 8);

      final asset = await db.select(db.assets).getSingle();
      expect(asset.vaultType, VaultType.qorovul);
      final txs = await db.select(db.vaultTransactions).get();
      expect(txs.map((t) => t.vaultAssetId).toSet(), {'a1'});
      final balance = txs.fold<int>(
        0,
        (sum, t) =>
            sum +
            (t.type == VaultTransactionType.deposit
                ? t.amountMinor
                : -t.amountMinor),
      );
      expect(balance, 195000000);
      final h = await _household(db);
      expect(h['reserve_monthly_estimate_minor'], isNull);
      expect(h['gate_bypassed_at'], isNull);
    },
  );

  test(
    'v8 → v9: nasiya qarzi saqlanadi va toʻlov rejasi toʻldiriladi',
    () async {
      final schema = await verifier.schemaAt(8);
      const ts = "'2026-10-01T09:00:00.000Z'";
      const meta = "'h1', $ts, $ts";
      schema.rawDatabase
        ..execute(
          'INSERT INTO households (id, household_id, created_at, updated_at) '
          "VALUES ('h1', $meta)",
        )
        ..execute(
          'INSERT INTO debts (id, household_id, created_at, updated_at, '
          'creditor_type, creditor_name, currency, principal_minor, '
          "remaining_minor, due_date) VALUES ('d1', $meta, 'shop', 'Doʻkon', "
          "'uzs', 30000000, 12000000, '2026-11-01')",
        )
        ..execute(
          'INSERT INTO debts (id, household_id, created_at, updated_at, '
          'creditor_type, creditor_name, currency, principal_minor, '
          "remaining_minor) VALUES ('d2', $meta, 'shop', 'Yopilgan', 'uzs', "
          '5000000, 0)',
        );
      final db = _open(schema.newConnection());
      addTearDown(db.close);
      await verifier.migrateAndValidate(db, 9);

      final debts = await db.select(db.debts).get();
      expect(debts, hasLength(2));
      expect(debts.first.scheduleType, isNull);
      final plan = await db.select(db.debtInstallments).get();
      expect(plan, hasLength(1), reason: 'yopilgan qarzga reja kerak emas');
      expect(plan.single.debtId, 'd1');
      expect(plan.single.amountMinor, 12000000);
      expect(plan.single.dueOn, LocalDate(2026, 11, 1));
    },
  );

  test(
    'v9 → v10: qarz va toʻlovlar saqlanadi, rejim standart 70/20/10',
    () async {
      final schema = await verifier.schemaAt(9);
      const ts = "'2026-10-01T09:00:00.000Z'";
      const meta = "'h1', $ts, $ts";
      schema.rawDatabase
        ..execute(
          'INSERT INTO households (id, household_id, created_at, updated_at) '
          "VALUES ('h1', $meta)",
        )
        ..execute(
          'INSERT INTO debts (id, household_id, created_at, updated_at, '
          'creditor_type, creditor_name, currency, principal_minor, '
          "remaining_minor, schedule_type) VALUES ('d1', $meta, 'bank', "
          "'Bank', 'uzs', 100000000, 60000000, 'annuity')",
        )
        ..execute(
          'INSERT INTO debt_payments (id, household_id, created_at, '
          'updated_at, debt_id, amount_minor, currency, paid_on) '
          "VALUES ('p1', $meta, 'd1', 40000000, 'uzs', '2026-10-01')",
        );
      final db = _open(schema.newConnection());
      addTearDown(db.close);
      await verifier.migrateAndValidate(db, 10);

      final h = await db.select(db.households).getSingle();
      expect(h.budgetMode, BudgetMode.standard);
      expect(
        (h.recoveryNeedsBp, h.recoveryDebtBp, h.recoverySavingsBp),
        (7000, 2000, 1000),
      );
      expect(h.freedShareOfferPending, isFalse);
      final d = await db.select(db.debts).getSingle();
      expect(d.remainingMinor, 60000000);
      expect(d.payoffOrder, isNull);
      expect(d.prepayFeeBp, isNull);
      final p = await db.select(db.debtPayments).getSingle();
      expect(p.amountMinor, 40000000);
      expect(p.feeMinor, 0);
      expect(p.contributorId, isNull);
      expect(await db.select(db.sellableItems).get(), isEmpty);
      expect(await db.select(db.debtContributors).get(), isEmpty);
    },
  );

  test('v10 → v11: maqsad saqlanadi, marosim jadvallari boʻsh', () async {
    final schema = await verifier.schemaAt(10);
    const ts = "'2026-10-01T09:00:00.000Z'";
    const meta = "'h1', $ts, $ts";
    schema.rawDatabase
      ..execute(
        'INSERT INTO households (id, household_id, created_at, updated_at) '
        "VALUES ('h1', $meta)",
      )
      ..execute(
        'INSERT INTO goals (id, household_id, created_at, updated_at, title, '
        "target_minor, currency) VALUES ('g1', $meta, 'Kontrakt', "
        "1500000000, 'uzs')",
      );
    final db = _open(schema.newConnection());
    addTearDown(db.close);
    await verifier.migrateAndValidate(db, 11);
    final g = await db.select(db.goals).getSingle();
    expect(g.title, 'Kontrakt');
    expect(g.targetMinor, 1500000000);
    expect(await db.select(db.ceremonyPlans).get(), isEmpty);
    expect(await db.select(db.goalContributions).get(), isEmpty);
  });

  test('v11 → v12: marosim saqlanadi, sheriklik jadvallari boʻsh', () async {
    final schema = await verifier.schemaAt(11);
    const ts = "'2026-10-01T09:00:00.000Z'";
    const meta = "'h1', $ts, $ts";
    schema.rawDatabase
      ..execute(
        'INSERT INTO households (id, household_id, created_at, updated_at) '
        "VALUES ('h1', $meta)",
      )
      ..execute(
        'INSERT INTO ceremony_plans (id, household_id, created_at, '
        'updated_at, title, type, status, currency) '
        "VALUES ('c1', $meta, 'Toʻy', 'toy', 'draft', 'uzs')",
      );
    final db = _open(schema.newConnection());
    addTearDown(db.close);
    await verifier.migrateAndValidate(db, 12);
    expect((await db.select(db.ceremonyPlans).getSingle()).title, 'Toʻy');
    expect(await db.select(db.partnerships).get(), isEmpty);
    expect(await db.select(db.partnershipContracts).get(), isEmpty);
  });

  test('v12 → v13: sheriklik saqlanadi, daftar jadvallari boʻsh', () async {
    final schema = await verifier.schemaAt(12);
    const ts = "'2026-10-01T09:00:00.000Z'";
    const meta = "'h1', $ts, $ts";
    schema.rawDatabase
      ..execute(
        'INSERT INTO households (id, household_id, created_at, updated_at) '
        "VALUES ('h1', $meta)",
      )
      ..execute(
        'INSERT INTO partnerships (id, household_id, created_at, updated_at, '
        'title, type, status, currency, term_months, report_period, '
        'end_terms, dispute_terms) VALUES '
        "('p1', $meta, 'Sex', 'mudaraba', 'active', 'uzs', 12, 'monthly', "
        "'a', 'b')",
      );
    final db = _open(schema.newConnection());
    addTearDown(db.close);
    await verifier.migrateAndValidate(db, 13);
    expect((await db.select(db.partnerships).getSingle()).title, 'Sex');
    expect(await db.select(db.ventureEntries).get(), isEmpty);
    expect(await db.select(db.offerChecks).get(), isEmpty);
  });

  test(
    'v13 → v14: mavjud foydalanuvchi onboardingʻdan oʻtgan hisoblanadi',
    () async {
      final schema = await verifier.schemaAt(13);
      const ts = "'2026-10-01T09:00:00.000Z'";
      schema.rawDatabase.execute(
        'INSERT INTO households (id, household_id, created_at, updated_at) '
        "VALUES ('h1', 'h1', $ts, $ts)",
      );
      final db = _open(schema.newConnection());
      addTearDown(db.close);
      await verifier.migrateAndValidate(db, 14);
      final h = await db.select(db.households).getSingle();
      expect(h.onboardedAt, isNotNull);
      expect(h.incomeKind, isNull);
    },
  );

  test(
    "v15 → v16: eski taklif tekshiruvlari yo'qolmaydi, yangi ustunlar bo'sh",
    () async {
      final schema = await verifier.schemaAt(15);
      const ts = "'2026-10-01T09:00:00.000Z'";
      schema.rawDatabase
        ..execute(
          'INSERT INTO households (id, household_id, created_at, updated_at) '
          "VALUES ('h1', 'h1', $ts, $ts)",
        )
        ..execute(
          'INSERT INTO offer_checks (id, household_id, created_at, updated_at, '
          'title, answers_json, verdict) '
          "VALUES ('o1', 'h1', $ts, $ts, 'Tez Foyda', "
          """'{"guaranteed":"yes"}', 'red')""",
        );
      final db = _open(schema.newConnection());
      addTearDown(db.close);
      await verifier.migrateAndValidate(db, 16);
      final row = await db.select(db.offerChecks).getSingle();
      expect(row.title, 'Tez Foyda');
      expect(row.verdict, OfferVerdict.red);
      expect(row.answersJson, '{"guaranteed":"yes"}');
      expect(row.amountMinor, isNull);
      expect(row.decision, isNull);
    },
  );

  test('v14 → v15: tilxat va shartnoma Agreement ga, tarix jurnalga', () async {
    final schema = await verifier.schemaAt(14);
    const ts = "'2026-09-01T09:00:00.000Z'";
    String row(String id) => "'$id', 'h1', $ts, $ts";
    final terms = const ContractTerms(
      title: 'Sex',
      type: PartnershipType.musharaka,
      currency: CurrencyCode.uzs,
      termMonths: 12,
      reportPeriod: ReportPeriod.monthly,
      endTerms: 'Sotib, kapitalga mutanosib',
      disputeTerms: 'Oqsoqol',
      partners: [
        ContractParty(
          name: 'Akmal',
          role: PartnerRole.both,
          shareBp: 5000,
          capital: [],
        ),
        ContractParty(
          name: 'Jasur',
          role: PartnerRole.both,
          shareBp: 5000,
          capital: [],
        ),
      ],
      witnesses: [],
    ).toJson().replaceAll("'", "''");
    const c = '(id, household_id, created_at, updated_at';
    schema.rawDatabase
      ..execute('INSERT INTO households $c) VALUES (${row('h1')})')
      ..execute(
        'INSERT INTO members $c, display_name, role, is_owner) '
        "VALUES (${row('m1')}, 'Akmal', 'adult', 1)",
      )
      ..execute(
        'INSERT INTO debts $c, creditor_type, creditor_name, currency, '
        'principal_minor, remaining_minor, start_date) '
        "VALUES (${row('d1')}, 'relative', 'Togʻa', 'uzs', 100000000, "
        "60000000, '2026-09-01')",
      )
      ..execute(
        'INSERT INTO debt_installments $c, debt_id, due_on, amount_minor, '
        "currency) VALUES (${row('i1')}, 'd1', '2026-12-01', 100000000, "
        "'uzs')",
      )
      ..execute(
        'INSERT INTO debt_payments $c, debt_id, amount_minor, currency, '
        "paid_on) VALUES (${row('pay1')}, 'd1', 40000000, 'uzs', "
        "'2026-09-20')",
      )
      ..execute(
        'INSERT INTO loan_signers $c, document_id, role, name, '
        "signature_png, signed_at) VALUES (${row('s1')}, 'd1', 'lender', "
        "'Togʻa', X'0102', $ts)",
      )
      ..execute(
        'INSERT INTO loan_signers $c, document_id, role, name) '
        "VALUES (${row('s2')}, 'd1', 'borrower', 'Akmal')",
      )
      ..execute(
        'INSERT INTO receivables $c, debtor_name, principal_minor, '
        'remaining_minor, currency, due_date) '
        "VALUES (${row('r1')}, 'Bobur', 5000000, 2000000, 'uzs', "
        "'2026-11-01')",
      )
      ..execute(
        'INSERT INTO loan_signers $c, document_id, role, name) '
        "VALUES (${row('s3')}, 'r1', 'lender', 'Akmal')",
      )
      ..execute(
        'INSERT INTO debts $c, creditor_type, creditor_name, currency, '
        'principal_minor, remaining_minor) '
        "VALUES (${row('d2')}, 'bank', 'Bank', 'uzs', 1, 1)",
      )
      ..execute(
        'INSERT INTO partnerships $c, title, type, status, currency, '
        'term_months, report_period, end_terms, dispute_terms, '
        "start_date) VALUES (${row('p1')}, 'Sex', 'musharaka', 'active', "
        "'uzs', 12, 'monthly', 'Sotib', 'Oqsoqol', '2026-09-01')",
      )
      ..execute(
        'INSERT INTO partners $c, partnership_id, name, role, '
        "profit_share_bp, is_me, sort_order) VALUES (${row('pa')}, 'p1', "
        "'Akmal', 'both', 5000, 1, 0)",
      )
      ..execute(
        'INSERT INTO partners $c, partnership_id, name, role, '
        "profit_share_bp, sort_order) VALUES (${row('pd')}, 'p1', "
        "'Jasur', 'both', 5000, 1)",
      )
      ..execute(
        'INSERT INTO capital_contributions $c, partnership_id, partner_id, '
        "kind, title, amount_minor, currency) VALUES (${row('k1')}, 'p1', "
        "'pa', 'cash', 'Naqd', 300000000, 'uzs')",
      )
      ..execute(
        'INSERT INTO partnership_contracts $c, partnership_id, '
        'contract_version, template_id, terms_json) VALUES '
        "(${row('ct1')}, 'p1', 1, 'musharaka-v1', '$terms')",
      )
      ..execute(
        'INSERT INTO loan_signers $c, document_id, role, name, '
        "signature_png, signed_at) VALUES (${row('s4')}, 'ct1', 'party', "
        "'Akmal', X'01', $ts)",
      )
      ..execute(
        'INSERT INTO venture_entries $c, partnership_id, kind, title, '
        "amount_minor, currency, occurred_on) VALUES (${row('v1')}, 'p1', "
        "'income', 'Buyurtma', 400000000, 'uzs', '2026-09-10')",
      )
      ..execute(
        'INSERT INTO venture_entries $c, partnership_id, kind, title, '
        'amount_minor, currency, occurred_on, deleted_at) VALUES '
        "(${row('v2')}, 'p1', 'expense', 'Oʻchirilgan', 1, 'uzs', "
        "'2026-09-11', $ts)",
      )
      ..execute(
        'INSERT INTO venture_periods $c, partnership_id, start_date, '
        'end_date, income_minor, expense_minor, net_minor, currency) '
        "VALUES (${row('vp1')}, 'p1', '2026-09-01', '2026-09-30', "
        "400000000, 0, 400000000, 'uzs')",
      )
      ..execute(
        'INSERT INTO distribution_shares $c, period_id, partner_id, '
        "amount_minor, currency) VALUES (${row('sh1')}, 'vp1', 'pa', "
        "200000000, 'uzs')",
      )
      ..execute(
        'INSERT INTO distribution_shares $c, period_id, partner_id, '
        "amount_minor, currency) VALUES (${row('sh2')}, 'vp1', 'pd', "
        "200000000, 'uzs')",
      );
    final db = _open(schema.newConnection());
    addTearDown(db.close);
    await verifier.migrateAndValidate(db, 15);

    final agreements = await db.select(db.agreements).get();
    expect(agreements, hasLength(3), reason: 'bank qarzi imzosiz — yoʻq');
    expect(agreements.every((a) => a.legacy), isTrue);
    final loan = agreements.singleWhere((a) => a.sourceId == 'd1');
    expect(loan.type, AgreementType.loan);
    expect(loan.status, AgreementStatus.draft, reason: 'bitta imzo yoʻq');
    final versions = await db.select(db.agreementVersions).get();
    // Versiya ID si = eski hujjat ID si — imzolar joyida.
    expect(versions.map((v) => v.id).toSet(), {'d1', 'r1', 'ct1'});
    final partnership = agreements.singleWhere((a) => a.sourceId == 'p1');
    expect(partnership.status, AgreementStatus.active);
    final answers = AgreementAnswers.decode(
      versions.singleWhere((v) => v.id == 'ct1').answersJson,
    );
    expect(answers.parties.map((p) => p.id), ['pa', 'pd']);
    expect(answers.profit.shares, {'pa': 5000, 'pd': 5000});

    final clock = FakeClock();
    final journal = DriftJournalRepository(
      db,
      SyncMetaFactory(UuidV7Generator(clock: clock), clock),
    );
    final loanChain = await journal.forAgreement(loan.id);
    expect(loanChain.map((e) => e.kind), [
      JournalKind.contribution,
      JournalKind.loanPayment,
    ]);
    expect(loanChain.last.amount!.minorUnits, 40000000);
    expect(verifyChain(loanChain), isNull);
    final pChain = await journal.forAgreement(partnership.id);
    expect(pChain.map((e) => e.kind), [
      JournalKind.contribution,
      JournalKind.ventureIncome,
      JournalKind.profitDistribution,
      JournalKind.profitDistribution,
    ], reason: 'oʻchirilgan kassa yozuvi kirmaydi');
    expect(verifyChain(pChain), isNull);
    final recv = agreements.singleWhere((a) => a.sourceId == 'r1');
    expect(
      (await journal.forAgreement(recv.id)).last.amount!.minorUnits,
      3000000,
    );

    // Append-only: DB darajasida o'zgartirish va o'chirish rad etiladi.
    await expectLater(
      db.customStatement(
        'UPDATE journal_entries SET amount_minor = 1 WHERE seq = 1',
      ),
      throwsA(anything),
    );
    await expectLater(
      db.customStatement('DELETE FROM journal_entries'),
      throwsA(anything),
    );
    expect(verifyChain(await journal.forAgreement(loan.id)), isNull);
  });

  // Har yangi versiya uchun: (oldingi, yangi).
  const upgradePaths = <(int, int)>[
    (1, 2),
    (2, 3),
    (3, 4),
    (4, 5),
    (5, 6),
    (6, 7),
    (7, 8),
    (8, 9),
    (9, 10),
    (10, 11),
    (11, 12),
    (12, 13),
    (13, 14),
    (14, 15),
    (15, 16),
    (1, 16),
  ];
  for (final (from, to) in upgradePaths) {
    test('migratsiya v$from → v$to', () async {
      final connection = await verifier.startAt(from);
      final db = _open(connection);
      addTearDown(db.close);
      await verifier.migrateAndValidate(db, to);
    });
  }
}

/// Oraliq versiyadagi `households` qatori (joriy klasslarsiz).
Future<Map<String, Object?>> _household(AppDatabase db) async =>
    (await db.customSelect('SELECT * FROM households').getSingle()).data;
