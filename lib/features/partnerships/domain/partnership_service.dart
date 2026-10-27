import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/security/pin/pin_service.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement_service.dart';
import 'package:baraka_daftari/features/agreements/domain/journal.dart';
import 'package:baraka_daftari/features/debts/domain/debts.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';
import 'package:baraka_daftari/features/household/domain/member_pin_service.dart';
import 'package:baraka_daftari/features/partnerships/domain/contract_template.dart';
import 'package:baraka_daftari/features/partnerships/domain/partnership.dart';
import 'package:baraka_daftari/features/partnerships/domain/partnership_rules.dart';
import 'package:baraka_daftari/features/vault/domain/reserve.dart';
import 'package:meta/meta.dart';

/// Tayyorgarlik darvozasi holatini beradi (Vazifa 9, `VaultService`).
typedef GateSource = Future<GateState> Function();

/// Bitta sheriklik: tomonlar, kapital, joriy shartnoma va imzolar,
/// oilaviy rozilik, buyout.
@immutable
final class PartnershipView {
  const PartnershipView({
    required this.partnership,
    required this.partners,
    required this.capital,
    required this.contracts,
    required this.signers,
    required this.adults,
    required this.consentedBy,
    required this.buyoutPayments,
    required this.today,
  });

  final Partnership partnership;
  final List<Partner> partners;
  final List<CapitalContribution> capital;

  /// Barcha versiyalar (o'sib boruvchi); oxirgisi — joriy.
  final List<PartnershipContract> contracts;

  /// Joriy versiya imzolovchilari (tomonlar va guvohlar).
  final List<LoanSigner> signers;
  final List<Member> adults;
  final Set<String> consentedBy;
  final List<BuyoutPayment> buyoutPayments;
  final LocalDate today;

  CurrencyCode get currency => partnership.currency;

  PartnershipContract get contract => contracts.last;

  ContractTerms get terms => ContractTerms.fromJson(contract.termsJson);

  ContractTemplate get template => ContractTemplate.byId(contract.templateId);

  Money capitalOf(Partner p) => Money.sum([
    for (final c in capital)
      if (c.partnerId == p.meta.id) c.amount,
  ], currency);

  Money get totalCapital => Money.sum(capital.map((c) => c.amount), currency);

  Partner? get me => partners.where((p) => p.isMe).firstOrNull;

  /// Ilova egasi kapital kiritadi — darvoza tekshiriladi (SPEC 2E.6).
  bool get meProvidesCapital {
    final m = me;
    return m != null && m.providesCapital && capitalOf(m).isPositive;
  }

  /// Ilova egasi kapital qabul qiladi (faqat mehnat) — darvoza yo'q, lekin
  /// «bu qarz emas» tushuntirishi va oilaviy rozilik majburiy.
  bool get meReceivesCapital => me?.role == PartnerRole.worker;

  bool get allSigned => signers.isNotEmpty && signers.every((s) => s.isSigned);

  bool get consentComplete =>
      adults.isNotEmpty && adults.every((a) => consentedBy.contains(a.meta.id));

  /// Faol sheriklikda yangi versiya hali imzolanmagan.
  bool get needsResign =>
      partnership.status == PartnershipStatus.active && !allSigned;

  /// Buyout: kapital egalarining ulushi (sotib olinadigan qism).
  Money get providerStake => Money.sum([
    for (final p in partners)
      if (p.role == PartnerRole.capitalProvider) capitalOf(p),
  ], currency);

  Money get buyoutPaid =>
      Money.sum(buyoutPayments.map((p) => p.amount), currency);

  Money get buyoutRemaining {
    final r = providerStake - buyoutPaid;
    return r.isNegative ? Money.zero(currency) : r;
  }

  List<BuyoutRow> get buyout => partnership.buyoutMonthly == null
      ? const []
      : buyoutSchedule(
          providerStake: providerStake,
          totalCapital: totalCapital,
          monthly: partnership.buyoutMonthly!,
          firstDue: today.plusMonths(1),
          paid: buyoutPaid,
        );
}

/// 5-qonun: sheriklik domeni (SPEC 2E.1, 2E.2, 2E.6).
class PartnershipService {
  PartnershipService({
    required HouseholdRepository households,
    required MemberRepository members,
    required MemberPinService memberPins,
    required PartnershipRepository partnerships,
    required PartnerRepository partners,
    required CapitalContributionRepository capital,
    required PartnershipContractRepository contracts,
    required LoanSignerRepository signers,
    required BuyoutPaymentRepository buyouts,
    required PartnershipConsentRepository consents,
    required GateSource gate,
    required SyncMetaFactory metaFactory,
    required Clock clock,
    AgreementLink? agreements,
  }) : _households = households,
       _agreements = agreements,
       _members = members,
       _memberPins = memberPins,
       _partnerships = partnerships,
       _partners = partners,
       _capital = capital,
       _contracts = contracts,
       _signers = signers,
       _buyouts = buyouts,
       _consents = consents,
       _gate = gate,
       _meta = metaFactory,
       _clock = clock;

  static const errNameRequired = 'partnership_name_required';
  static const errTermRequired = 'partnership_term_required';
  static const errContractUnsigned = 'partnership_contract_unsigned';
  static const errGateClosed = 'partnership_gate_closed';
  static const errConsentRequired = 'partnership_family_consent_required';
  static const errNotDebtAck = 'partnership_not_debt_ack_required';
  static const errClosed = 'partnership_closed';
  static const errAdultOnly = 'partnership_adult_only';
  static const errNotPositive = 'partnership_amount_must_be_positive';
  static const errMeRequired = 'partnership_me_required';
  static const errAlreadySigned = 'partnership_already_signed';

  /// Shartnoma = `Agreement(PARTNERSHIP)`: 9 savol to'liq bo'lmaguncha
  /// imzolab bo'lmaydi (SPEC 2F.2).
  static const errAgreementIncomplete = 'partnership_agreement_incomplete';

  final AgreementLink? _agreements;

  final HouseholdRepository _households;
  final MemberRepository _members;
  final MemberPinService _memberPins;
  final PartnershipRepository _partnerships;
  final PartnerRepository _partners;
  final CapitalContributionRepository _capital;
  final PartnershipContractRepository _contracts;
  final LoanSignerRepository _signers;
  final BuyoutPaymentRepository _buyouts;
  final PartnershipConsentRepository _consents;
  final GateSource _gate;
  final SyncMetaFactory _meta;
  final Clock _clock;

  LocalDate get today => Tashkent.dateOf(_clock.nowUtc());

  Future<List<Partnership>> list() async =>
      _partnerships.listActive((await _households.current()).meta.id);

  /// Shartnoma ustasi natijasi (SPEC 2E.2): sheriklik **faqat shartnoma
  /// bilan** yaratiladi — 1-versiya va imzolovchilar (tomonlar, guvohlar).
  Future<Partnership> create({
    required String title,
    required PartnershipType type,
    required List<PartnerDraft> partners,
    required int termMonths,
    required ReportPeriod reportPeriod,
    required String endTerms,
    required String disputeTerms,
    List<String> witnesses = const [],
  }) async {
    if (title.trim().isEmpty) throw const DomainRuleException(errNameRequired);
    if (termMonths <= 0 ||
        endTerms.trim().isEmpty ||
        disputeTerms.trim().isEmpty) {
      throw const DomainRuleException(errTermRequired);
    }
    final h = await _households.current();
    PartnershipRules.validate(type, partners, h.baseCurrency);
    if (partners.where((p) => p.isMe).length != 1) {
      throw const DomainRuleException(errMeRequired);
    }
    final hh = h.meta.id;
    final p = await _partnerships.add(
      Partnership(
        meta: _meta.create(hh),
        title: title.trim(),
        type: type,
        currency: h.baseCurrency,
        termMonths: termMonths,
        reportPeriod: reportPeriod,
        endTerms: endTerms.trim(),
        disputeTerms: disputeTerms.trim(),
      ),
    );
    for (final (i, d) in partners.indexed) {
      final partner = await _partners.add(
        Partner(
          meta: _meta.create(hh),
          partnershipId: p.meta.id,
          name: d.name.trim(),
          role: d.role,
          profitShareBp: d.profit.basisPoints!,
          isMe: d.isMe,
          sortOrder: i,
        ),
      );
      for (final c in d.capital) {
        await _capital.add(
          CapitalContribution(
            meta: _meta.create(hh),
            partnershipId: p.meta.id,
            partnerId: partner.meta.id,
            kind: c.kind,
            title: c.title.trim(),
            amount: c.amount,
          ),
        );
      }
    }
    await _newVersion(
      p,
      version: 1,
      witnesses: [
        for (final w in witnesses)
          if (w.trim().isNotEmpty) w.trim(),
      ],
    );
    return p;
  }

  /// Joriy shartlardan yangi shartnoma versiyasi va imzolovchilar (hammasi
  /// imzosiz — qayta imzolash).
  Future<PartnershipContract> _newVersion(
    Partnership p, {
    required int version,
    required List<String> witnesses,
  }) async {
    final hh = p.meta.householdId;
    final partners = await _partners.forPartnership(p.meta.id);
    final capital = await _capital.forPartnership(p.meta.id);
    final terms = ContractTerms(
      title: p.title,
      type: p.type,
      currency: p.currency,
      termMonths: p.termMonths,
      reportPeriod: p.reportPeriod,
      endTerms: p.endTerms,
      disputeTerms: p.disputeTerms,
      partners: [
        for (final x in partners)
          ContractParty(
            name: x.name,
            role: x.role,
            shareBp: x.profitShareBp,
            capital: [
              for (final c in capital)
                if (c.partnerId == x.meta.id)
                  CapitalItem(kind: c.kind, title: c.title, amount: c.amount),
            ],
          ),
      ],
      witnesses: witnesses,
    );
    final contract = await _contracts.add(
      PartnershipContract(
        meta: _meta.create(hh),
        partnershipId: p.meta.id,
        version: version,
        templateId: ContractTemplate.forType(p.type).id,
        termsJson: terms.toJson(),
      ),
    );
    for (final x in partners) {
      await _signers.add(
        LoanSigner(
          meta: _meta.create(hh),
          documentId: contract.meta.id,
          role: SignerRole.party,
          name: x.name,
        ),
      );
    }
    for (final w in witnesses) {
      await _signers.add(
        LoanSigner(
          meta: _meta.create(hh),
          documentId: contract.meta.id,
          role: SignerRole.witness,
          name: w,
        ),
      );
    }
    final me = partners.indexWhere((x) => x.isMe);
    await _agreements?.partnershipVersion(
      partnershipId: p.meta.id,
      contractId: contract.meta.id,
      version: version,
      terms: terms,
      partyIds: [for (final x in partners) x.meta.id],
      start: p.startDate ?? today,
      myIndex: me < 0 ? null : me,
    );
    return contract;
  }

  Future<Partnership> _fresh(Partnership p) async =>
      await _partnerships.findById(p.meta.id) ?? p;

  Future<List<Member>> _adults(String hh) async => [
    for (final m in await _members.listActive(hh))
      if (m.role == MemberRole.adult) m,
  ];

  Future<PartnershipView> view(Partnership partnership) async {
    final p = await _fresh(partnership);
    final contracts = await _contracts.forPartnership(p.meta.id);
    return PartnershipView(
      partnership: p,
      partners: await _partners.forPartnership(p.meta.id),
      capital: await _capital.forPartnership(p.meta.id),
      contracts: contracts,
      signers: await _signers.forDocument(contracts.last.meta.id),
      adults: await _adults(p.meta.householdId),
      consentedBy: {
        for (final c in await _consents.forPartnership(p.meta.id)) c.memberId,
      },
      buyoutPayments: await _buyouts.forPartnership(p.meta.id),
      today: today,
    );
  }

  /// Imzo (tomon yoki guvoh, shu qurilmada). Joriy versiyani hamma
  /// imzolagach qoralama `SIGNED` bo'ladi.
  Future<PartnershipView> sign(
    Partnership p,
    LoanSigner signer,
    String name,
    List<int> png,
  ) async {
    if (name.trim().isEmpty) throw const DomainRuleException(errNameRequired);
    if (png.isEmpty) throw const DomainRuleException(errNotPositive);
    final fresh = await _fresh(p);
    if (fresh.status == PartnershipStatus.closed) {
      throw const DomainRuleException(errClosed);
    }
    // Imzo bazadan tekshiriladi (ekrandagi nusxa eskirgan bo'lishi mumkin):
    // imzolangan tomon qayta imzolamaydi — aks holda imzo jim almashadi.
    final contracts = await _contracts.forPartnership(fresh.meta.id);
    final stored = await _signers.forDocument(contracts.last.meta.id);
    if (stored.any((s) => s.meta.id == signer.meta.id && s.isSigned)) {
      throw const DomainRuleException(errAlreadySigned);
    }
    final ready = await _agreements?.readiness(
      AgreementSource.partnership,
      fresh.meta.id,
    );
    if (ready != null && !ready.complete) {
      throw const DomainRuleException(errAgreementIncomplete);
    }
    await _signers.update(
      signer.copyWith(
        name: name.trim(),
        signaturePng: png,
        signedAt: _clock.nowUtc(),
      ),
    );
    final v = await view(fresh);
    if (v.allSigned && fresh.status == PartnershipStatus.draft) {
      await _partnerships.update(
        fresh.copyWith(status: PartnershipStatus.signed),
      );
      await _agreements?.setStatus(
        AgreementSource.partnership,
        fresh.meta.id,
        AgreementStatus.signed,
      );
      return view(fresh);
    }
    return v;
  }

  Future<LoanSigner> addWitness(Partnership p, String name) async {
    if (name.trim().isEmpty) throw const DomainRuleException(errNameRequired);
    final v = await view(p);
    if (v.partnership.status != PartnershipStatus.draft) {
      throw const DomainRuleException(errContractUnsigned);
    }
    return _signers.add(
      LoanSigner(
        meta: _meta.create(p.meta.householdId),
        documentId: v.contract.meta.id,
        role: SignerRole.witness,
        name: name.trim(),
      ),
    );
  }

  /// Shartnomaga o'zgarish (SPEC 2E.2): **yangi versiya** va hamma qayta
  /// imzolaydi. Imzolangan (hali faol emas) — qoralamaga qaytadi; faol
  /// sheriklik faol qoladi, lekin `needsResign`.
  Future<PartnershipContract> amend(
    Partnership partnership, {
    int? termMonths,
    ReportPeriod? reportPeriod,
    String? endTerms,
    String? disputeTerms,
    Map<String, int>? sharesBp,
  }) async {
    final p = await _fresh(partnership);
    if (p.status == PartnershipStatus.closed) {
      throw const DomainRuleException(errClosed);
    }
    if (termMonths != null && termMonths <= 0) {
      throw const DomainRuleException(errTermRequired);
    }
    final v = await view(p);
    if (sharesBp != null) {
      // Ulushlar ham faqat foiz — qoidalar qayta tekshiriladi.
      PartnershipRules.validate(p.type, [
        for (final x in v.partners)
          PartnerDraft(
            name: x.name,
            role: x.role,
            isMe: x.isMe,
            profit: ProfitShareInput.percent(
              sharesBp[x.meta.id] ?? x.profitShareBp,
            ),
            capital: [
              for (final c in v.capital)
                if (c.partnerId == x.meta.id)
                  CapitalItem(kind: c.kind, title: c.title, amount: c.amount),
            ],
          ),
      ], p.currency);
      for (final x in v.partners) {
        final bp = sharesBp[x.meta.id];
        if (bp != null && bp != x.profitShareBp) {
          await _partners.update(x.copyWith(profitShareBp: bp));
        }
      }
    }
    final next = p.contractVersion + 1;
    final updated = await _partnerships.update(
      p.copyWith(
        termMonths: termMonths ?? p.termMonths,
        reportPeriod: reportPeriod ?? p.reportPeriod,
        endTerms: endTerms?.trim().isEmpty ?? true ? p.endTerms : endTerms!,
        disputeTerms: disputeTerms?.trim().isEmpty ?? true
            ? p.disputeTerms
            : disputeTerms!,
        contractVersion: next,
        status: p.status == PartnershipStatus.signed
            ? PartnershipStatus.draft
            : p.status,
      ),
    );
    return _newVersion(
      updated,
      version: next,
      witnesses: v.terms.witnesses,
    );
  }

  /// Kapital qabul qiluvchi: «bu qarz emas» tushuntirishi o'qildi.
  Future<Partnership> acknowledgeNotDebt(Partnership p) async => _partnerships
      .update((await _fresh(p)).copyWith(notDebtAcknowledged: true));

  /// Kapital qabul qilishga katta a'zoning roziligi (PIN bo'lsa — PIN).
  Future<PinCheck> consent(Partnership p, Member member, String pin) async {
    if (member.role != MemberRole.adult) {
      throw const DomainRuleException(errAdultOnly);
    }
    final check = await _memberPins.verify(member, pin);
    if (check is! PinAccepted) return check;
    final existing = await _consents.forPartnership(p.meta.id);
    if (!existing.any((c) => c.memberId == member.meta.id)) {
      await _consents.add(
        PartnershipConsent(
          meta: _meta.create(p.meta.householdId),
          partnershipId: p.meta.id,
          memberId: member.meta.id,
        ),
      );
    }
    return check;
  }

  /// Faollashtirish (SPEC 2E.6):
  /// * joriy shartnoma hamma tomonidan imzolangan bo'lishi shart;
  /// * **kapital kirituvchi** — tayyorgarlik darvozasi ochiq bo'lishi kerak
  ///   (yopiq bo'lsa faqat ongli chetlab o'tish, qayd etiladi);
  /// * **kapital qabul qiluvchi** — darvoza yo'q, lekin «bu qarz emas»
  ///   tushuntirishi va barcha kattalarning roziligi majburiy.
  Future<Partnership> activate(
    Partnership partnership, {
    bool gateBypassConfirmed = false,
  }) async {
    final v = await view(partnership);
    final p = v.partnership;
    if (p.status == PartnershipStatus.closed) {
      throw const DomainRuleException(errClosed);
    }
    if (p.status == PartnershipStatus.active) return p;
    if (!v.allSigned) throw const DomainRuleException(errContractUnsigned);
    if (v.meProvidesCapital) {
      final gate = await _gate();
      if (!gate.isOpen) {
        if (!gateBypassConfirmed) {
          throw const DomainRuleException(errGateClosed);
        }
        final h = await _households.current();
        await _households.update(
          h.copyWith(gateBypassedAt: _clock.nowUtc()),
        );
      }
    }
    if (v.meReceivesCapital) {
      if (!p.notDebtAcknowledged) {
        throw const DomainRuleException(errNotDebtAck);
      }
      if (!v.consentComplete) {
        throw const DomainRuleException(errConsentRequired);
      }
    }
    final active = await _partnerships.update(
      p.copyWith(
        status: PartnershipStatus.active,
        startDate: p.startDate ?? today,
      ),
    );
    await _agreements?.setStatus(
      AgreementSource.partnership,
      p.meta.id,
      AgreementStatus.active,
    );
    return active;
  }

  Future<Partnership> close(Partnership p) async {
    final closed = await _partnerships.update(
      (await _fresh(p)).copyWith(status: PartnershipStatus.closed),
    );
    await _agreements?.setStatus(
      AgreementSource.partnership,
      p.meta.id,
      AgreementStatus.closed,
    );
    return closed;
  }

  // --- Buyout (kamayib boruvchi musharaka) ---

  Future<Partnership> setBuyout(Partnership p, Money monthly) async {
    if (!monthly.isPositive) throw const DomainRuleException(errNotPositive);
    return _partnerships.update(
      (await _fresh(p)).copyWith(buyoutMonthly: monthly),
    );
  }

  Future<BuyoutPayment> recordBuyout(Partnership p, Money amount) async {
    if (!amount.isPositive) throw const DomainRuleException(errNotPositive);
    final v = await view(p);
    if (amount > v.buyoutRemaining) {
      throw const DomainRuleException(errNotPositive);
    }
    final payment = await _buyouts.add(
      BuyoutPayment(
        meta: _meta.create(p.meta.householdId),
        partnershipId: p.meta.id,
        amount: amount,
        paidOn: today,
      ),
    );
    await _agreements?.record(
      AgreementSource.partnership,
      p.meta.id,
      JournalDraft(
        kind: JournalKind.buyout,
        date: today,
        amount: amount,
        refId: payment.meta.id,
      ),
    );
    return payment;
  }
}
