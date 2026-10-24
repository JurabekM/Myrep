import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/agreements/domain/accountability.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement.dart';
import 'package:baraka_daftari/features/agreements/domain/builders.dart';
import 'package:baraka_daftari/features/agreements/domain/completeness.dart';
import 'package:baraka_daftari/features/agreements/domain/journal.dart';
import 'package:baraka_daftari/features/debts/domain/debts.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';
import 'package:baraka_daftari/features/partnerships/domain/contract_template.dart';
import 'package:meta/meta.dart';

/// Mavjud modullar (qarz, bergan qarz, sheriklik) kelishuv dvigateli bilan
/// shu interfeys orqali bog'lanadi (SPEC 2F.1 refaktori).
abstract interface class AgreementLink {
  /// Bog'langan kelishuv imzolashga tayyormi: 9/9 (yoki 9A dan oldingi
  /// legacy). Kelishuv yo'q bo'lsa — `null`.
  Future<Completeness?> readiness(AgreementSource source, String sourceId);

  /// Jurnalga yozuv (kelishuv bo'lsa); bo'lmasa — hech narsa.
  Future<void> record(
    AgreementSource source,
    String sourceId,
    JournalDraft draft,
  );

  /// Bog'langan kelishuv holatini moslash (masalan, sheriklik faollashdi).
  Future<void> setStatus(
    AgreementSource source,
    String sourceId,
    AgreementStatus status,
  );

  /// Bog'langan kelishuvning to'liq ko'rinishi (holat, tomonlar, jurnal) yoki
  /// `null` — kelishuv yo'q. Taqsimot gate'lari shundan o'qiydi (2F.7, 2F.8).
  Future<AgreementView?> viewBySource(AgreementSource source, String sourceId);

  /// Moliyaviy yozuv [date] sanasi bilan yozilishi mumkinligini tekshiradi:
  /// ko'rik bayonnomasidan keyin qulflangan davrga faqat tuzatuvchi yozuv
  /// (SPEC 2F.5). Kelishuv bo'lmasa — hech narsa. Yozishdan OLDIN chaqiriladi.
  Future<void> ensureWritable(
    AgreementSource source,
    String sourceId,
    JournalKind kind,
    LocalDate date,
  );

  /// Sheriklik shartnomasining yangi versiyasi (versiya ID si = shartnoma
  /// qatori ID si; imzolar o'sha `document_id` da).
  Future<Agreement> partnershipVersion({
    required String partnershipId,
    required String contractId,
    required int version,
    required ContractTerms terms,
    required List<String> partyIds,
    required LocalDate start,
    int? myIndex,
  });
}

/// Kelishuv ko'rinishi: joriy versiya, to'liqlik, imzolar va jurnal.
@immutable
final class AgreementView {
  const AgreementView({
    required this.agreement,
    required this.versions,
    required this.completeness,
    required this.signers,
    required this.journal,
    required this.brokenAt,
  });

  final Agreement agreement;
  final List<AgreementVersion> versions;
  final Completeness completeness;
  final List<LoanSigner> signers;
  final List<JournalEntry> journal;

  /// Zanjirdagi birinchi buzilgan yozuv (`null` — butun).
  final int? brokenAt;

  AgreementVersion get current => versions.last;
  AgreementAnswers get answers => current.answers;

  /// Imzolash ochiqmi: 9/9 (legacy — oldin imzolangan, o'z kuchida).
  bool get canSign => completeness.complete || agreement.legacy;

  bool get anySigned => signers.any((s) => s.isSigned);
  bool get allSigned => signers.isNotEmpty && signers.every((s) => s.isSigned);

  /// Joriy versiya tahrirlanadimi (qoralama va hali hech kim imzolamagan).
  bool get editable => agreement.status == AgreementStatus.draft && !anySigned;
}

/// Og'zaki kelishuvni yozib olishda «shu kungacha» holat (SPEC 2F.9).
@immutable
final class OpeningLine {
  const OpeningLine({required this.partyId, required this.amount, this.note});

  final String partyId;
  final Money amount;
  final String? note;
}

/// Umumiy kelishuv dvigateli (SPEC 2F, MVP_PLAN Vazifa 9A).
class AgreementService implements AgreementLink {
  AgreementService({
    required HouseholdRepository households,
    required AgreementRepository agreements,
    required AgreementVersionRepository versions,
    required JournalRepository journal,
    required LoanSignerRepository signers,
    required SyncMetaFactory metaFactory,
    required Clock clock,
  }) : _households = households,
       _agreements = agreements,
       _versions = versions,
       _journal = journal,
       _signers = signers,
       _meta = metaFactory,
       _clock = clock;

  static const errTitleRequired = 'agreement_title_required';
  static const errIncomplete = 'agreement_incomplete';
  static const errNotEditable = 'agreement_version_signed';
  static const errClosed = 'agreement_closed';
  static const errFutureDate = 'agreement_oral_future_date';
  static const errNameRequired = 'signer_name_required';
  static const errEmptySignature = 'signature_empty';
  static const errAlreadySigned = 'agreement_already_signed';
  static const errNotSigned = 'agreement_not_signed';
  static const errNoChange = 'agreement_no_change';

  final HouseholdRepository _households;
  final AgreementRepository _agreements;
  final AgreementVersionRepository _versions;
  final JournalRepository _journal;
  final LoanSignerRepository _signers;
  final SyncMetaFactory _meta;
  final Clock _clock;

  LocalDate get today => Tashkent.dateOf(_clock.nowUtc());

  Future<List<Agreement>> list() async =>
      _agreements.listActive((await _households.current()).meta.id);

  Future<Agreement?> find(String id) async {
    final a = await _agreements.findById(id);
    return a == null || a.meta.deletedAt != null ? null : a;
  }

  Future<Agreement?> bySource(AgreementSource s, String id) =>
      _agreements.bySource(s, id);

  /// Tilxat uchun qaytarish jadvali bormi (3-savol, `LOAN`) — bog'langan
  /// qarzda jadval doim bor (qarz jadvalsiz saqlanmaydi, Vazifa 10).
  bool _hasSchedule(Agreement a) =>
      a.type == AgreementType.loan && a.source != null;

  Future<AgreementView> view(Agreement agreement) async {
    final a = await _agreements.findById(agreement.meta.id) ?? agreement;
    final versions = await _versions.forAgreement(a.meta.id);
    final journal = await _journal.forAgreement(a.meta.id);
    return AgreementView(
      agreement: a,
      versions: versions,
      completeness: checkCompleteness(
        a.type,
        versions.last.answers,
        hasSchedule: _hasSchedule(a),
      ),
      signers: await _signers.forDocument(versions.last.meta.id),
      journal: journal,
      brokenAt: verifyChain(journal),
    );
  }

  /// Yangi kelishuv (ijara, xizmat, oilaviy, boshqa): 1-versiya qoralama.
  /// Tomonlar ([parties]) 1-savolga yoziladi.
  Future<Agreement> create({
    required AgreementType type,
    required String title,
    required List<AgreementParty> parties,
    LocalDate? effectiveFrom,
  }) async {
    if (title.trim().isEmpty) {
      throw const DomainRuleException(errTitleRequired);
    }
    final hh = (await _households.current()).meta.id;
    final from = effectiveFrom ?? today;
    // Kelishuv va 9-savoldagi yangilash sanasi bir xil: yillik eslatma
    // kelishuvning `reviewDate` idan rejalashtiriladi.
    final review = defaultReviewDate(from);
    final a = await _agreements.add(
      Agreement(
        meta: _meta.create(hh),
        type: type,
        title: title.trim(),
        effectiveFrom: from,
        reviewDate: review,
      ),
    );
    await _versions.add(
      AgreementVersion(
        meta: _meta.create(hh),
        agreementId: a.meta.id,
        version: 1,
        answers: AgreementAnswers(
          parties: parties,
          term: TermRule(reviewDate: review),
        ),
      ),
    );
    return a;
  }

  /// Og'zaki kelishuvni yozib olish (SPEC 2F.9): `effectiveFrom` o'tmishda,
  /// shu kungacha holat — `OPENING_BALANCE` jurnal yozuvlari. Tomonlar uni
  /// ham imzolab tasdiqlaydi (kelishuv bilan birga).
  Future<Agreement> recordOral({
    required AgreementType type,
    required String title,
    required List<AgreementParty> parties,
    required LocalDate effectiveFrom,
    required List<OpeningLine> opening,
    String? openingNote,
  }) async {
    if (effectiveFrom.isAfter(today)) {
      throw const DomainRuleException(errFutureDate);
    }
    final created = await create(
      type: type,
      title: title,
      parties: parties,
      effectiveFrom: effectiveFrom,
    );
    final oral = await _agreements.update(
      Agreement(
        meta: created.meta,
        type: created.type,
        title: created.title,
        effectiveFrom: created.effectiveFrom,
        oral: true,
        reviewDate: created.reviewDate,
      ),
    );
    if (opening.isEmpty) {
      await _journal.append(
        oral.meta.id,
        JournalDraft(
          kind: JournalKind.openingBalance,
          date: today,
          note: openingNote,
        ),
      );
    }
    for (final o in opening) {
      await _journal.append(
        oral.meta.id,
        JournalDraft(
          kind: JournalKind.openingBalance,
          date: today,
          partyId: o.partyId,
          amount: o.amount,
          note: o.note ?? openingNote,
        ),
      );
    }
    return oral;
  }

  /// Joriy versiya javoblarini saqlash — faqat qoralamada va hech kim
  /// imzolamagan bo'lsa (imzolangan versiya o'zgarmaydi — [newVersion]).
  Future<AgreementView> saveAnswers(
    Agreement agreement,
    AgreementAnswers answers,
  ) async {
    final v = await view(agreement);
    if (!v.editable) throw const DomainRuleException(errNotEditable);
    await _versions.update(v.current.copyWith(answers: answers));
    await _syncReviewDate(v.agreement, answers);
    await _syncSigners(v, answers);
    return view(v.agreement);
  }

  /// Hali hech kim imzolamagan imzolovchilar ro'yxatini javoblarga moslash:
  /// mustaqil kelishuvda — qaytadan (tomonlar o'zgargan bo'lishi mumkin);
  /// bog'langanida (tilxat, shartnoma) — faqat hakam.
  Future<void> _syncSigners(AgreementView v, AgreementAnswers answers) async {
    if (v.signers.isEmpty || v.anySigned) return;
    final a = v.agreement;
    if (a.source == null) {
      for (final s in v.signers) {
        await _signers.softDelete(s.meta.id);
      }
      final fresh = await view(a);
      if (fresh.canSign) await prepareSigning(a);
      return;
    }
    final name = answers.arbiter?.name.trim() ?? '';
    final arbiters = [
      for (final s in v.signers)
        if (s.role == SignerRole.arbiter) s,
    ];
    for (final s in arbiters) {
      if (s.name != name) await _signers.softDelete(s.meta.id);
    }
    if (name.isNotEmpty && !arbiters.any((s) => s.name == name)) {
      await _signers.add(
        LoanSigner(
          meta: _meta.create(a.meta.householdId),
          documentId: v.current.meta.id,
          role: SignerRole.arbiter,
          name: name,
        ),
      );
    }
  }

  Future<void> _syncReviewDate(Agreement a, AgreementAnswers answers) async {
    final r = answers.term.reviewDate;
    if (r != null && r != a.reviewDate) {
      final fresh = await _agreements.findById(a.meta.id) ?? a;
      await _agreements.update(fresh.copyWith(reviewDate: r));
    }
  }

  /// Yangi versiya (har o'zgarish — yangi versiya va qayta imzo, SPEC
  /// 2F.3). Javobsiz chaqiruv va [note] — yillik yangilash «o'zgarishsiz
  /// tasdiqlandi».
  Future<AgreementView> newVersion(
    Agreement agreement, {
    AgreementAnswers? answers,
    String? note,
  }) async {
    final v = await view(agreement);
    final a = v.agreement;
    if (a.status == AgreementStatus.closed) {
      throw const DomainRuleException(errClosed);
    }
    if (v.editable) {
      // Hali imzolanmagan qoralama — yangi versiya shart emas.
      return answers == null ? v : saveAnswers(a, answers);
    }
    final next = a.currentVersion + 1;
    final hh = a.meta.householdId;
    final body = answers ?? v.answers;
    await _versions.add(
      AgreementVersion(
        meta: _meta.create(hh),
        agreementId: a.meta.id,
        version: next,
        answers: body,
        note: note,
      ),
    );
    await _agreements.update(
      a.copyWith(
        currentVersion: next,
        status: AgreementStatus.draft,
        reviewDate: body.term.reviewDate,
      ),
    );
    return view(a);
  }

  /// Imzolash bosqichini ochish: 9/9 bo'lishi shart. Imzolovchilar
  /// (tomonlar, guvohlar, hakam) joriy versiyaga yaratiladi.
  Future<AgreementView> prepareSigning(Agreement agreement) async {
    final v = await view(agreement);
    if (!v.canSign) throw const DomainRuleException(errIncomplete);
    final hh = v.agreement.meta.householdId;
    final doc = v.current.meta.id;
    final existing = v.signers;
    Future<void> add(SignerRole role, String name) => _signers.add(
      LoanSigner(
        meta: _meta.create(hh),
        documentId: doc,
        role: role,
        name: name,
      ),
    );
    final hasParties = existing.any(
      (s) =>
          s.role == SignerRole.party ||
          s.role == SignerRole.lender ||
          s.role == SignerRole.borrower,
    );
    if (!hasParties) {
      for (final p in v.answers.parties) {
        await add(SignerRole.party, p.name);
      }
    }
    final witnesses = {
      for (final s in existing)
        if (s.role == SignerRole.witness) s.name,
    };
    for (final w in v.answers.witnesses) {
      if (!witnesses.contains(w)) await add(SignerRole.witness, w);
    }
    final arbiter = v.answers.arbiter;
    if (arbiter != null &&
        arbiter.name.trim().isNotEmpty &&
        !existing.any((s) => s.role == SignerRole.arbiter)) {
      await add(SignerRole.arbiter, arbiter.name.trim());
    }
    return view(v.agreement);
  }

  /// Imzo (shu qurilmada): 9/9 bo'lmasa — taqiq. Hamma imzolagach
  /// qoralama `SIGNED` bo'ladi.
  Future<AgreementView> sign(
    Agreement agreement,
    LoanSigner signer,
    String name,
    List<int> png,
  ) async {
    if (name.trim().isEmpty) throw const DomainRuleException(errNameRequired);
    if (png.isEmpty) throw const DomainRuleException(errEmptySignature);
    final v = await view(agreement);
    if (v.agreement.status == AgreementStatus.closed) {
      throw const DomainRuleException(errClosed);
    }
    if (!v.canSign) throw const DomainRuleException(errIncomplete);
    // Imzolagan tomon qayta imzolamaydi (imzo jim almashmasin).
    if (v.signers.any((s) => s.meta.id == signer.meta.id && s.isSigned)) {
      throw const DomainRuleException(errAlreadySigned);
    }
    await _signers.update(
      signer.copyWith(
        name: name.trim(),
        signaturePng: png,
        signedAt: _clock.nowUtc(),
      ),
    );
    final after = await view(v.agreement);
    if (after.allSigned && after.agreement.status == AgreementStatus.draft) {
      await _agreements.update(
        after.agreement.copyWith(status: AgreementStatus.signed),
      );
      return view(after.agreement);
    }
    return after;
  }

  /// Imzolangan kelishuvni kuchga kiritish (ijara, xizmat, oilaviy…).
  Future<Agreement> activate(Agreement agreement) async {
    final v = await view(agreement);
    if (v.agreement.status != AgreementStatus.signed) {
      throw const DomainRuleException(errNotSigned);
    }
    return _agreements.update(
      v.agreement.copyWith(status: AgreementStatus.active),
    );
  }

  /// Jurnalga tuzatuvchi yozuv (eski yozuv o'zgarmaydi).
  Future<JournalEntry> correct(
    Agreement agreement, {
    required String note,
    Money? amount,
    String? partyId,
    String? refId,
  }) => _journal.append(
    agreement.meta.id,
    JournalDraft(
      kind: JournalKind.correction,
      date: today,
      amount: amount,
      partyId: partyId,
      note: note,
      refId: refId,
    ),
  );

  Future<int?> verify(Agreement agreement) async =>
      verifyChain(await _journal.forAgreement(agreement.meta.id));

  /// Qarz / bergan qarz tilxati: kelishuv bo'lmasa — yaratiladi (versiya ID
  /// si = [documentId], imzolar shu hujjatda). Jurnal: qarz berilishi va
  /// mavjud to'lovlar ([payments]).
  Future<Agreement> ensureLoan({
    required AgreementSource source,
    required String documentId,
    required String lender,
    required String borrower,
    required bool meIsLender,
    required Money principal,
    required LocalDate start,
    LocalDate? lastDue,
    String? earlyTerms,
    List<JournalDraft> payments = const [],
  }) async {
    final existing = await _agreements.bySource(source, documentId);
    if (existing != null) return existing;
    final hh = (await _households.current()).meta.id;
    final signers = await _signers.forDocument(documentId);
    final signed = signers.isNotEmpty && signers.every((s) => s.isSigned);
    final a = await _agreements.add(
      Agreement(
        meta: _meta.create(hh),
        type: AgreementType.loan,
        title: meIsLender ? borrower : lender,
        effectiveFrom: start,
        status: signed ? AgreementStatus.signed : AgreementStatus.draft,
        source: source,
        sourceId: documentId,
        // Oldin to'liq imzolangan tilxat — 9 savolsiz ham o'z kuchida.
        legacy: signed,
      ),
    );
    final answers = loanAnswers(
      lender: lender,
      borrower: borrower,
      meIsLender: meIsLender,
      principal: principal,
      start: start,
      lastDue: lastDue,
      earlyTerms: earlyTerms,
    );
    await _versions.add(
      AgreementVersion(
        meta: _meta.create(hh).copyWith(id: documentId),
        agreementId: a.meta.id,
        version: 1,
        answers: answers,
      ),
    );
    await _syncReviewDate(a, answers);
    await _journal.append(
      a.meta.id,
      JournalDraft(
        kind: JournalKind.contribution,
        date: start,
        partyId: lenderPartyId,
        amount: principal,
        refId: documentId,
      ),
    );
    for (final p in payments) {
      await _journal.append(a.meta.id, p);
    }
    return a;
  }

  @override
  Future<Completeness?> readiness(
    AgreementSource source,
    String sourceId,
  ) async {
    final a = await _agreements.bySource(source, sourceId);
    if (a == null) return null;
    final v = await view(a);
    return v.canSign
        ? const Completeness(missing: [], errors: [], warnings: [])
        : v.completeness;
  }

  @override
  Future<void> record(
    AgreementSource source,
    String sourceId,
    JournalDraft draft,
  ) async {
    final a = await _agreements.bySource(source, sourceId);
    if (a != null) await _journal.append(a.meta.id, draft);
  }

  @override
  Future<void> setStatus(
    AgreementSource source,
    String sourceId,
    AgreementStatus status,
  ) async {
    final a = await _agreements.bySource(source, sourceId);
    if (a != null && a.status != status) {
      await _agreements.update(a.copyWith(status: status));
    }
  }

  @override
  Future<AgreementView?> viewBySource(
    AgreementSource source,
    String sourceId,
  ) async {
    final a = await _agreements.bySource(source, sourceId);
    return a == null ? null : view(a);
  }

  @override
  Future<void> ensureWritable(
    AgreementSource source,
    String sourceId,
    JournalKind kind,
    LocalDate date,
  ) async {
    final a = await _agreements.bySource(source, sourceId);
    if (a == null) return;
    assertWritable(await _journal.forAgreement(a.meta.id), kind, date);
  }

  @override
  Future<Agreement> partnershipVersion({
    required String partnershipId,
    required String contractId,
    required int version,
    required ContractTerms terms,
    required List<String> partyIds,
    required LocalDate start,
    int? myIndex,
  }) async {
    final hh = (await _households.current()).meta.id;
    var a = await _agreements.bySource(
      AgreementSource.partnership,
      partnershipId,
    );
    AgreementAnswers? keep;
    if (a == null) {
      a = await _agreements.add(
        Agreement(
          meta: _meta.create(hh),
          type: AgreementType.partnership,
          title: terms.title,
          effectiveFrom: start,
          currentVersion: version,
          source: AgreementSource.partnership,
          sourceId: partnershipId,
        ),
      );
    } else {
      // 3, 6, 8-savollar va qo'shimchalar oldingi versiyadan o'tadi.
      keep = (await _versions.forAgreement(a.meta.id)).last.answers;
      a = await _agreements.update(
        a.copyWith(
          currentVersion: version,
          status: AgreementStatus.draft,
          title: terms.title,
        ),
      );
    }
    final answers = partnershipAnswers(
      terms: terms,
      partyIds: partyIds,
      start: start,
      myIndex: myIndex,
      keep: keep,
    );
    await _versions.add(
      AgreementVersion(
        meta: _meta.create(hh).copyWith(id: contractId),
        agreementId: a.meta.id,
        version: version,
        answers: answers,
      ),
    );
    await _syncReviewDate(a, answers);
    return a;
  }
}
