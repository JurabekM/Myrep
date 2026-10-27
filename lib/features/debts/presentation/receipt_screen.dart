import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/app/widgets/text_prompt.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/pdf/baraka_pdf.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/agreements/data/agreement_providers.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement.dart';
import 'package:baraka_daftari/features/agreements/domain/builders.dart';
import 'package:baraka_daftari/features/agreements/domain/journal.dart';
import 'package:baraka_daftari/features/agreements/presentation/agreement_labels.dart';
import 'package:baraka_daftari/features/agreements/presentation/agreement_screen.dart';
import 'package:baraka_daftari/features/content/data/content_providers.dart';
import 'package:baraka_daftari/features/content/domain/content.dart';
import 'package:baraka_daftari/features/debts/data/debt_providers.dart';
import 'package:baraka_daftari/features/debts/domain/debts.dart';
import 'package:baraka_daftari/features/debts/domain/loan_receipt_pdf.dart';
import 'package:baraka_daftari/features/debts/presentation/signature_pad.dart';
import 'package:baraka_daftari/features/household/presentation/member_views.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:share_plus/share_plus.dart';

/// Tilxat mazmuni (qarz yoki bergan qarz uchun bir xil).
@immutable
final class ReceiptSubject {
  const ReceiptSubject({
    required this.documentId,
    required this.lender,
    required this.borrower,
    required this.amount,
    required this.date,
    required this.plan,
    required this.source,
    required this.meIsLender,
    this.reason,
    this.markup,
    this.earlyTerms,
    this.payments = const [],
  });

  final String documentId;

  /// Tilxat = `Agreement(LOAN)` (Vazifa 9A): manba va jurnal uchun.
  final AgreementSource source;
  final bool meIsLender;
  final String? earlyTerms;

  /// Mavjud to'lovlar (kelishuv birinchi marta yaratilganda jurnalga).
  final List<JournalDraft> payments;
  final String lender;
  final String borrower;
  final Money amount;
  final LocalDate date;

  /// (sana, summa) qatorlari.
  final List<(LocalDate, Money)> plan;
  final String? reason;

  /// Foiz / ustama jami; `null` — qarzi hasana.
  final Money? markup;
}

/// Qarz tilxati (SPEC 2D.5): tomonlar va guvohlar shu qurilmada imzolaydi,
/// PDF yaratiladi va ulashiladi.
class ReceiptScreen extends ConsumerWidget {
  const ReceiptScreen.debt({required this.id, super.key}) : isDebt = true;
  const ReceiptScreen.receivable({required this.id, super.key})
    : isDebt = false;

  final String id;
  final bool isDebt;

  Future<ReceiptSubject?> _subject(WidgetRef ref, String me) async {
    if (isDebt) {
      final v = await ref.read(debtViewProvider(id).future);
      if (v == null) return null;
      final d = v.debt;
      return ReceiptSubject(
        documentId: d.meta.id,
        source: AgreementSource.debt,
        meIsLender: false,
        lender: d.creditorName,
        borrower: me,
        amount: d.principal,
        date: d.startDate ?? Tashkent.dateOf(d.meta.createdAt),
        plan: [for (final i in v.plan) (i.dueOn, i.amount)],
        reason: d.reason,
        markup: v.cost.overpayment.isPositive ? v.cost.overpayment : null,
        earlyTerms: d.earlyRepaymentTerms,
        payments: [
          for (final p in v.payments)
            JournalDraft(
              kind: JournalKind.loanPayment,
              date: p.paidOn,
              partyId: borrowerPartyId,
              amount: p.amount,
              note: p.note,
              refId: p.meta.id,
            ),
        ],
      );
    }
    final r = await ref.read(receivableProvider(id).future);
    if (r == null) return null;
    final returned = r.principal - r.remaining;
    return ReceiptSubject(
      documentId: r.meta.id,
      source: AgreementSource.receivable,
      meIsLender: true,
      lender: me,
      borrower: r.debtorName,
      amount: r.principal,
      date: Tashkent.dateOf(r.meta.createdAt),
      plan: [(r.dueDate, r.principal)],
      reason: r.reason,
      payments: [
        if (returned.isPositive)
          JournalDraft(
            kind: JournalKind.loanPayment,
            date: Tashkent.dateOf(r.meta.updatedAt),
            partyId: borrowerPartyId,
            amount: returned,
          ),
      ],
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final members = ref.watch(membersProvider).valueOrNull;
    if (members == null) {
      return Scaffold(
        appBar: AppBar(title: Text(l10n.debtReceipt)),
        body: const Center(child: CircularProgressIndicator()),
      );
    }
    final owner = members.where((m) => m.isOwner).firstOrNull;
    final me = owner == null ? l10n.memberOwnerDefault : l10n.member(owner);
    return FutureBuilder<ReceiptSubject?>(
      future: _subject(ref, me),
      builder: (context, snap) => Scaffold(
        appBar: AppBar(title: Text(l10n.debtReceipt)),
        body: switch (snap) {
          AsyncSnapshot(hasData: true, :final data?) => _ReceiptBody(
            subject: data,
          ),
          AsyncSnapshot(connectionState: ConnectionState.done) => Center(
            child: Text(l10n.genericError),
          ),
          _ => const Center(child: CircularProgressIndicator()),
        },
      ),
    );
  }
}

class _ReceiptBody extends ConsumerStatefulWidget {
  const _ReceiptBody({required this.subject});

  final ReceiptSubject subject;

  @override
  ConsumerState<_ReceiptBody> createState() => _ReceiptBodyState();
}

class _ReceiptBodyState extends ConsumerState<_ReceiptBody> {
  List<LoanSigner>? _signers;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  Agreement? _agreement;

  Future<void> _reload() async {
    final s = widget.subject;
    final agreements = await ref.read(agreementServiceProvider.future);
    final agreement = await agreements.ensureLoan(
      source: s.source,
      documentId: s.documentId,
      lender: s.lender,
      borrower: s.borrower,
      meIsLender: s.meIsLender,
      principal: s.amount,
      start: s.date,
      lastDue: s.plan.isEmpty ? null : s.plan.last.$1,
      earlyTerms: s.earlyTerms,
      payments: s.payments,
    );
    await (await ref.read(
      loanReceiptServiceProvider.future,
    )).signers(s.documentId, borrower: s.borrower, lender: s.lender);
    // 9/9 bo'lsa — hakam va guvohlar imzolovchilar ro'yxatiga qo'shiladi.
    final v = await agreements.view(agreement);
    if (v.canSign) await agreements.prepareSigning(agreement);
    final list = (await agreements.view(agreement)).signers;
    _agreement = agreement;
    ref.invalidate(agreementBySourceProvider(s.source, s.documentId));
    if (mounted) setState(() => _signers = list);
  }

  Future<void> _sign(LoanSigner signer) async {
    final l10n = context.l10n;
    final messenger = ScaffoldMessenger.of(context);
    final result = await showSignDialog(
      context,
      role: l10n.signerRole(signer.role),
      name: signer.name,
    );
    final agreement = _agreement;
    if (result == null || agreement == null) return;
    try {
      final s = await ref.read(agreementServiceProvider.future);
      final after = await s.sign(agreement, signer, result.$1, result.$2);
      // Kelishuv ekrani (agar ochiq bo'lsa) yangi imzoni ko'rsin.
      ref.invalidate(agreementViewProvider(agreement.meta.id));
      if (after.agreement.status == AgreementStatus.signed &&
          agreement.status == AgreementStatus.draft) {
        await recordTaskEvent(ref, TaskTrigger.agreementSigned);
      }
    } on DomainRuleException catch (e) {
      messenger.showSnackBar(SnackBar(content: Text(agError(l10n, e.code))));
    }
    await _reload();
  }

  Future<void> _addWitness() async {
    final l10n = context.l10n;
    final messenger = ScaffoldMessenger.of(context);
    final name = await showTextPrompt(
      context,
      title: l10n.witnessAdd,
      label: l10n.memberName,
      fieldKey: const Key('witness-name'),
      okKey: const Key('witness-save'),
    );
    if (name == null || name.trim().isEmpty) return;
    final agreement = _agreement;
    if (agreement == null) return;
    // Guvoh kelishuv javoblariga yoziladi: tilxat va kelishuv bitta manbadan.
    try {
      final agreements = await ref.read(agreementServiceProvider.future);
      final v = await agreements.view(agreement);
      await agreements.saveAnswers(
        agreement,
        v.answers.copyWith(witnesses: [...v.answers.witnesses, name.trim()]),
      );
    } on DomainRuleException catch (e) {
      messenger.showSnackBar(SnackBar(content: Text(agError(l10n, e.code))));
      return;
    }
    ref.invalidate(agreementViewProvider(agreement.meta.id));
    await _reload();
  }

  LoanReceiptDoc _doc(BuildContext context) {
    final l10n = context.l10n;
    final money = context.money;
    final s = widget.subject;
    final today = Tashkent.dateOf(ref.read(clockProvider).nowUtc());
    return LoanReceiptDoc(
      title: l10n.receiptPdfTitle,
      // PDF shriftida «→» yo'q — tire ishlatiladi.
      subtitle: '${s.lender} — ${s.borrower}',
      partiesHeading: l10n.receiptPdfParties,
      details: [
        (l10n.roleLender, s.lender),
        (l10n.roleBorrower, s.borrower),
        (l10n.receiptPdfAmount, money(s.amount)),
        (l10n.receiptPdfDate, formatDate(s.date)),
        if (s.reason != null) (l10n.receiptPdfReason, s.reason!),
        (
          l10n.receiptPdfMarkup,
          s.markup == null ? l10n.receiptPdfNoMarkup : money(s.markup!),
        ),
      ],
      planHeading: l10n.debtScheduleLabel,
      planHeaders: [l10n.receiptPdfDate, l10n.receiptPdfPayment],
      planRows: [
        for (final (d, m) in s.plan) [formatDate(d), money(m)],
      ],
      note: l10n.receiptPdfNote,
      signaturesHeading: l10n.receiptPdfSignatures,
      signatures: [
        for (final x in _signers ?? const <LoanSigner>[])
          PdfSignature(
            role: l10n.signerRole(x.role),
            name: x.name,
            image: x.signaturePng == null
                ? null
                : Uint8List.fromList(x.signaturePng!),
            signedAt: x.signedAt == null
                ? null
                : formatDate(Tashkent.dateOf(x.signedAt!)),
          ),
      ],
      footer: '${l10n.appTitle} · ${formatDate(today)}',
    );
  }

  Future<void> _share() async {
    final l10n = context.l10n;
    final messenger = ScaffoldMessenger.of(context);
    final doc = _doc(context);
    setState(() => _busy = true);
    try {
      final fonts = await PdfFonts.load(rootBundle);
      final bytes = await buildLoanReceiptPdf(fonts, doc);
      await SharePlus.instance.share(
        ShareParams(
          files: [
            XFile.fromData(
              bytes,
              mimeType: 'application/pdf',
              name: 'qarz_tilxati.pdf',
            ),
          ],
          fileNameOverrides: const ['qarz_tilxati.pdf'],
          subject: l10n.receiptPdfTitle,
        ),
      );
    } on Object {
      AppLog.event('receipt_share_failed');
      messenger.showSnackBar(SnackBar(content: Text(l10n.genericError)));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final money = context.money;
    final s = widget.subject;
    final signers = _signers;
    // Kelishuv o'zgarsa (kelishuv ekranidan imzo) tilxat qayta yuklanadi.
    final aid = _agreement?.meta.id;
    if (aid != null) {
      ref.listen(agreementViewProvider(aid), (_, _) {
        if (mounted) _reload();
      });
    }
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
      children: [
        Text(l10n.receiptHint),
        const SizedBox(height: 8),
        AgreementLinkCard(source: s.source, sourceId: s.documentId),
        Card(
          child: ListTile(
            title: Text('${s.lender} — ${s.borrower}'),
            subtitle: Text(
              [
                money(s.amount),
                for (final (d, m) in s.plan) '${formatDate(d)}: ${money(m)}',
              ].join('\n'),
            ),
          ),
        ),
        const SizedBox(height: 8),
        if (signers == null)
          const LinearProgressIndicator()
        else
          for (final x in signers)
            ListTile(
              key: Key('signer-${x.meta.id}'),
              leading: Icon(
                x.isSigned ? Icons.check_circle : Icons.draw_outlined,
                color: x.isSigned
                    ? Theme.of(context).colorScheme.primary
                    : null,
              ),
              title: Text(x.name),
              subtitle: Text(
                '${l10n.signerRole(x.role)}'
                '${x.isSigned ? ' · ${l10n.signed}' : ''}',
              ),
              // Imzolagan tomon qayta imzolamaydi.
              trailing: x.isSigned
                  ? null
                  : TextButton(
                      key: Key('sign-${x.role.name}-${x.meta.id}'),
                      onPressed: () => _sign(x),
                      child: Text(l10n.signAction),
                    ),
            ),
        Align(
          alignment: Alignment.centerLeft,
          child: TextButton.icon(
            key: const Key('witness-add'),
            icon: const Icon(Icons.add),
            label: Text(l10n.witnessAdd),
            onPressed: _addWitness,
          ),
        ),
        const SizedBox(height: 12),
        FilledButton.icon(
          key: const Key('receipt-share'),
          icon: const Icon(Icons.ios_share),
          label: Text(l10n.receiptShare),
          onPressed: _busy || signers == null ? null : _share,
        ),
      ],
    );
  }
}
