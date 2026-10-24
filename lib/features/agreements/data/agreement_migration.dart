import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement.dart';
import 'package:baraka_daftari/features/agreements/domain/builders.dart';
import 'package:baraka_daftari/features/agreements/domain/journal.dart';
import 'package:baraka_daftari/features/partnerships/domain/contract_template.dart';
import 'package:drift/drift.dart';

/// v14 → v15 (MVP_PLAN 9A, 1-bo'lim 6-band): 9A dan oldin yaratilgan qarz
/// tilxatlari (`LoanReceipt` — `loan_signers` dagi hujjatlar) va sheriklik
/// shartnomalari (`PartnershipContract`) `Agreement` ga ko'chiriladi.
///
/// * Versiya ID si = eski hujjat ID si (tilxatda — qarz ID, shartnomada —
///   `partnership_contracts` qatori) — imzolar joyida qoladi, ko'chirilmaydi.
/// * Mavjud moliyaviy yozuvlar (qarz to'lovlari, kapital, kassa daftari,
///   taqsimot, buyout) sana tartibida jurnalga yoziladi (xesh-zanjir).
/// * `legacy = true`: 9 savol to'liq bo'lmasligi mumkin, imzolar o'z kuchida.
///
/// Faqat xom SQL — keyingi sxema versiyalarining sinflariga bog'lanmaydi.
Future<void> migrateLegacyAgreementsV15(
  DatabaseConnectionUser db,
  SyncMetaFactory metaFactory,
) async {
  final hhRow = await db
      .customSelect(
        'SELECT id FROM households WHERE deleted_at IS NULL '
        'ORDER BY created_at LIMIT 1',
      )
      .getSingleOrNull();
  if (hhRow == null) return;
  final hh = hhRow.read<String>('id');
  final owner =
      (await db
              .customSelect(
                'SELECT display_name FROM members WHERE is_owner = 1 '
                'AND deleted_at IS NULL LIMIT 1',
              )
              .getSingleOrNull())
          ?.read<String>('display_name') ??
      '';
  final w = _Writer(db, metaFactory, hh);

  // --- Qarz tilxatlari
  final docs = await db
      .customSelect(
        'SELECT document_id, COUNT(*) AS total, '
        'SUM(CASE WHEN signature_png IS NOT NULL THEN 1 ELSE 0 END) AS signed '
        'FROM loan_signers WHERE deleted_at IS NULL GROUP BY document_id',
      )
      .get();
  for (final doc in docs) {
    final id = doc.read<String>('document_id');
    final allSigned = doc.read<int>('total') == doc.read<int>('signed');
    final debt = await db
        .customSelect(
          'SELECT * FROM debts WHERE id = ? AND deleted_at IS NULL',
          variables: [Variable.withString(id)],
        )
        .getSingleOrNull();
    if (debt != null) {
      final c = CurrencyCode.values.byName(debt.read<String>('currency'));
      final principal = Money(debt.read<int>('principal_minor'), c);
      final start =
          _date(debt.readNullable<String>('start_date')) ??
          _dayOf(debt.read<DateTime>('created_at'));
      final lastDue = await db
          .customSelect(
            'SELECT MAX(due_on) AS d FROM debt_installments '
            'WHERE debt_id = ? AND deleted_at IS NULL',
            variables: [Variable.withString(id)],
          )
          .getSingle();
      final creditor = debt.read<String>('creditor_name');
      final agreement = await w.agreement(
        type: AgreementType.loan,
        title: creditor,
        effectiveFrom: start,
        status: allSigned ? AgreementStatus.signed : AgreementStatus.draft,
        source: AgreementSource.debt,
        sourceId: id,
        versionId: id,
        answers: loanAnswers(
          lender: creditor,
          borrower: owner,
          meIsLender: false,
          principal: principal,
          start: start,
          lastDue: _date(lastDue.readNullable<String>('d')),
          earlyTerms: debt.readNullable<String>('early_repayment_terms'),
        ),
      );
      await w.journal(
        agreement,
        JournalKind.contribution,
        start,
        partyId: lenderPartyId,
        amount: principal,
        refId: id,
      );
      for (final p
          in await db
              .customSelect(
                'SELECT id, amount_minor, currency, paid_on, note FROM '
                'debt_payments WHERE debt_id = ? AND deleted_at IS NULL '
                'ORDER BY paid_on, created_at',
                variables: [Variable.withString(id)],
              )
              .get()) {
        await w.journal(
          agreement,
          JournalKind.loanPayment,
          LocalDate.parse(p.read<String>('paid_on')),
          partyId: borrowerPartyId,
          amount: Money(
            p.read<int>('amount_minor'),
            CurrencyCode.values.byName(p.read<String>('currency')),
          ),
          note: p.readNullable<String>('note'),
          refId: p.read<String>('id'),
        );
      }
      continue;
    }
    final r = await db
        .customSelect(
          'SELECT * FROM receivables WHERE id = ? AND deleted_at IS NULL',
          variables: [Variable.withString(id)],
        )
        .getSingleOrNull();
    if (r == null) continue;
    final c = CurrencyCode.values.byName(r.read<String>('currency'));
    final principal = Money(r.read<int>('principal_minor'), c);
    final start = _dayOf(r.read<DateTime>('created_at'));
    final debtor = r.read<String>('debtor_name');
    final agreement = await w.agreement(
      type: AgreementType.loan,
      title: debtor,
      effectiveFrom: start,
      status: allSigned ? AgreementStatus.signed : AgreementStatus.draft,
      source: AgreementSource.receivable,
      sourceId: id,
      versionId: id,
      answers: loanAnswers(
        lender: owner,
        borrower: debtor,
        meIsLender: true,
        principal: principal,
        start: start,
        lastDue: LocalDate.parse(r.read<String>('due_date')),
      ),
    );
    await w.journal(
      agreement,
      JournalKind.contribution,
      start,
      partyId: lenderPartyId,
      amount: principal,
      refId: id,
    );
    // Bergan qarzda to'lovlar alohida yozilmagan — qaytgan jami bitta yozuv.
    final returned = principal - Money(r.read<int>('remaining_minor'), c);
    if (returned.isPositive) {
      await w.journal(
        agreement,
        JournalKind.loanPayment,
        _dayOf(r.read<DateTime>('updated_at')),
        partyId: borrowerPartyId,
        amount: returned,
        refId: id,
      );
    }
  }

  // --- Sheriklik shartnomalari
  for (final p
      in await db
          .customSelect(
            'SELECT * FROM partnerships WHERE deleted_at IS NULL '
            'ORDER BY created_at',
          )
          .get()) {
    final pid = p.read<String>('id');
    final partners = await db
        .customSelect(
          'SELECT id, name, is_me FROM partners WHERE partnership_id = ? '
          'AND deleted_at IS NULL ORDER BY sort_order',
          variables: [Variable.withString(pid)],
        )
        .get();
    final ids = [for (final x in partners) x.read<String>('id')];
    final names = [for (final x in partners) x.read<String>('name')];
    final myIndex = partners.indexWhere((x) => x.read<bool>('is_me'));
    final start =
        _date(p.readNullable<String>('start_date')) ??
        _dayOf(p.read<DateTime>('created_at'));
    final contracts = await db
        .customSelect(
          'SELECT id, contract_version, terms_json FROM partnership_contracts '
          'WHERE partnership_id = ? AND deleted_at IS NULL '
          'ORDER BY contract_version',
          variables: [Variable.withString(pid)],
        )
        .get();
    if (contracts.isEmpty) continue;
    final status = switch (p.read<String>('status')) {
      'signed' => AgreementStatus.signed,
      'active' => AgreementStatus.active,
      'closed' => AgreementStatus.closed,
      _ => AgreementStatus.draft,
    };
    String? agreement;
    for (final ct in contracts) {
      final terms = ContractTerms.fromJson(ct.read<String>('terms_json'));
      // Eski versiyadagi sherik ismi bo'yicha qator ID si (topilmasa — tartib).
      final partyIds = [
        for (final (i, x) in terms.partners.indexed)
          names.contains(x.name)
              ? ids[names.indexOf(x.name)]
              : (i < ids.length ? ids[i] : 'p${i + 1}'),
      ];
      final answers = partnershipAnswers(
        terms: terms,
        partyIds: partyIds,
        start: start,
        myIndex: myIndex < 0 ? null : myIndex,
      );
      if (agreement == null) {
        agreement = await w.agreement(
          type: AgreementType.partnership,
          title: p.read<String>('title'),
          effectiveFrom: start,
          status: status,
          source: AgreementSource.partnership,
          sourceId: pid,
          versionId: ct.read<String>('id'),
          versionNo: ct.read<int>('contract_version'),
          answers: answers,
          currentVersion: p.read<int>('contract_version'),
        );
      } else {
        await w.version(
          agreement,
          ct.read<String>('id'),
          ct.read<int>('contract_version'),
          answers,
        );
      }
    }
    final events = <_Event>[];
    for (final x
        in await db
            .customSelect(
              'SELECT id, partner_id, title, amount_minor, currency, '
              'created_at FROM capital_contributions WHERE partnership_id = ? '
              'AND deleted_at IS NULL',
              variables: [Variable.withString(pid)],
            )
            .get()) {
      events.add(
        _Event(
          start,
          0,
          x.read<DateTime>('created_at'),
          JournalKind.contribution,
          partyId: x.read<String>('partner_id'),
          amount: _money(x),
          note: x.read<String>('title'),
          refId: x.read<String>('id'),
        ),
      );
    }
    for (final x
        in await db
            .customSelect(
              'SELECT id, kind, title, amount_minor, currency, occurred_on, '
              'created_at FROM venture_entries WHERE partnership_id = ? '
              'AND deleted_at IS NULL',
              variables: [Variable.withString(pid)],
            )
            .get()) {
      events.add(
        _Event(
          LocalDate.parse(x.read<String>('occurred_on')),
          1,
          x.read<DateTime>('created_at'),
          switch (x.read<String>('kind')) {
            'income' => JournalKind.ventureIncome,
            'expense' => JournalKind.ventureExpense,
            'forceMajeure' => JournalKind.forceMajeure,
            _ => JournalKind.correction,
          },
          amount: _money(x),
          note: x.read<String>('title'),
          refId: x.read<String>('id'),
        ),
      );
    }
    for (final x
        in await db
            .customSelect(
              'SELECT s.id, s.partner_id, s.amount_minor, s.currency, '
              'v.end_date, s.created_at FROM distribution_shares s '
              'JOIN venture_periods v ON v.id = s.period_id '
              'WHERE v.partnership_id = ? AND s.deleted_at IS NULL '
              'AND v.deleted_at IS NULL',
              variables: [Variable.withString(pid)],
            )
            .get()) {
      final amount = _money(x);
      events.add(
        _Event(
          LocalDate.parse(x.read<String>('end_date')),
          2,
          x.read<DateTime>('created_at'),
          amount.isNegative
              ? JournalKind.lossDistribution
              : JournalKind.profitDistribution,
          partyId: x.read<String>('partner_id'),
          amount: amount,
          refId: x.read<String>('id'),
        ),
      );
    }
    for (final x
        in await db
            .customSelect(
              'SELECT id, amount_minor, currency, paid_on, created_at FROM '
              'buyout_payments WHERE partnership_id = ? AND deleted_at IS NULL',
              variables: [Variable.withString(pid)],
            )
            .get()) {
      events.add(
        _Event(
          LocalDate.parse(x.read<String>('paid_on')),
          3,
          x.read<DateTime>('created_at'),
          JournalKind.buyout,
          amount: _money(x),
          refId: x.read<String>('id'),
        ),
      );
    }
    events.sort();
    for (final e in events) {
      await w.journal(
        agreement!,
        e.kind,
        e.date,
        partyId: e.partyId,
        amount: e.amount,
        note: e.note,
        refId: e.refId,
      );
    }
  }
}

Money _money(QueryRow x) => Money(
  x.read<int>('amount_minor'),
  CurrencyCode.values.byName(x.read<String>('currency')),
);

LocalDate? _date(String? iso) => iso == null ? null : LocalDate.parse(iso);

LocalDate _dayOf(DateTime utc) => Tashkent.dateOf(utc);

final class _Event implements Comparable<_Event> {
  _Event(
    this.date,
    this.order,
    this.created,
    this.kind, {
    this.partyId,
    this.amount,
    this.note,
    this.refId,
  });

  final LocalDate date;
  final int order;
  final DateTime created;
  final JournalKind kind;
  final String? partyId;
  final Money? amount;
  final String? note;
  final String? refId;

  @override
  int compareTo(_Event o) {
    final d = date.compareTo(o.date);
    if (d != 0) return d;
    final k = order.compareTo(o.order);
    return k != 0 ? k : created.compareTo(o.created);
  }
}

/// Xom SQL bilan yozuvchi (umumiy ustunlar va zanjir holati).
final class _Writer {
  _Writer(this.db, this.meta, this.hh);

  final DatabaseConnectionUser db;
  final SyncMetaFactory meta;
  final String hh;
  final Map<String, (int, String)> _chain = {};

  List<Variable<Object>> _common(SyncMeta m) => [
    Variable.withString(m.id),
    Variable.withString(m.householdId),
    Variable.withDateTime(m.createdAt),
    Variable.withDateTime(m.updatedAt),
  ];

  static const _cols = 'id, household_id, created_at, updated_at, version';

  Future<String> agreement({
    required AgreementType type,
    required String title,
    required LocalDate effectiveFrom,
    required AgreementStatus status,
    required AgreementSource source,
    required String sourceId,
    required String versionId,
    required AgreementAnswers answers,
    int versionNo = 1,
    int? currentVersion,
  }) async {
    final m = meta.create(hh);
    await db.customInsert(
      'INSERT INTO agreements ($_cols, type, status, title, effective_from, '
      'current_version, source, source_id, oral, legacy, review_date) '
      'VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, 0, 1, ?)',
      variables: [
        ..._common(m),
        Variable.withString(type.name),
        Variable.withString(status.name),
        Variable.withString(title),
        Variable.withString('$effectiveFrom'),
        Variable.withInt(currentVersion ?? versionNo),
        Variable.withString(source.name),
        Variable.withString(sourceId),
        Variable(answers.term.reviewDate?.toString()),
      ],
    );
    await version(m.id, versionId, versionNo, answers);
    return m.id;
  }

  Future<void> version(
    String agreementId,
    String id,
    int versionNo,
    AgreementAnswers answers,
  ) async {
    final m = meta.create(hh).copyWith(id: id);
    await db.customInsert(
      'INSERT INTO agreement_versions ($_cols, agreement_id, version_no, '
      'answers_json) VALUES (?, ?, ?, ?, 1, ?, ?, ?)',
      variables: [
        ..._common(m),
        Variable.withString(agreementId),
        Variable.withInt(versionNo),
        Variable.withString(answers.encode()),
      ],
    );
  }

  Future<void> journal(
    String agreementId,
    JournalKind kind,
    LocalDate date, {
    String? partyId,
    Money? amount,
    String? note,
    String? refId,
  }) async {
    final (seq, prev) = _chain[agreementId] ?? (0, genesisHash);
    final m = meta.create(hh);
    final hash = chainHash(
      prev,
      journalCanonical(
        id: m.id,
        agreementId: agreementId,
        kind: kind,
        date: date,
        partyId: partyId,
        amount: amount,
        note: note,
        refId: refId,
      ),
    );
    await db.customInsert(
      'INSERT INTO journal_entries ($_cols, agreement_id, seq, kind, '
      'party_id, amount_minor, currency, entry_date, note, ref_id, '
      'prev_hash, hash) '
      'VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
      variables: [
        ..._common(m),
        Variable.withString(agreementId),
        Variable.withInt(seq + 1),
        Variable.withString(kind.code),
        Variable(partyId),
        Variable(amount?.minorUnits),
        Variable(amount?.currency.name),
        Variable.withString('$date'),
        Variable(note),
        Variable(refId),
        Variable.withString(prev),
        Variable.withString(hash),
      ],
    );
    _chain[agreementId] = (seq + 1, hash);
  }
}
