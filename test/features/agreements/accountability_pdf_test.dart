import 'package:baraka_daftari/app/l10n/gen/app_localizations.dart';
import 'package:baraka_daftari/core/db/database_provider.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/pdf/baraka_pdf.dart';
import 'package:baraka_daftari/core/security/pin/pin_hasher.dart';
import 'package:baraka_daftari/core/security/secure_blob_store.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/agreements/data/agreement_providers.dart';
import 'package:baraka_daftari/features/agreements/domain/accountability.dart';
import 'package:baraka_daftari/features/agreements/domain/accountability_service.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement.dart';
import 'package:baraka_daftari/features/agreements/domain/journal.dart';
import 'package:baraka_daftari/features/agreements/presentation/accountability_pdf.dart';
import 'package:flutter/services.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../helpers/db.dart';
import '../../helpers/fakes.dart';

/// Hakam papkasi va ko'rik bayonnomasi bloklari (SPEC 2F.5, 2F.8): har bir
/// bo'lim bor va matnlar hisobotga tushadi («snapshot» — bo'limlar ro'yxati).
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  final l = lookupAppLocalizations(const Locale('uz'));
  String fmt(Money m) => '${m.minorUnits} ${m.currency.name}';

  late TestDb t;
  late ProviderContainer c;
  late AccountabilityService acc;
  late JournalRepository journal;

  LocalDate today() => Tashkent.dateOf(t.clock.nowUtc());

  setUp(() async {
    t = TestDb.open();
    c = ProviderContainer(
      overrides: [
        appDatabaseProvider.overrideWith((ref) async => t.db),
        clockProvider.overrideWithValue(t.clock),
        secureBlobStoreProvider.overrideWithValue(InMemorySecureBlobStore()),
        pinHasherProvider.overrideWithValue(ReferencePinHasher()),
      ],
    );
    addTearDown(c.dispose);
    acc = await c.read(accountabilityServiceProvider.future);
    journal = await c.read(journalRepositoryProvider.future);
  });

  Future<Agreement> withHistory() async {
    final s = await c.read(agreementServiceProvider.future);
    final a = await s.create(
      type: AgreementType.rent,
      title: 'Doʻkon ijarasi',
      parties: const [
        AgreementParty(id: 'p1', name: 'Akmal', isMe: true),
        AgreementParty(id: 'p2', name: 'Bahodir'),
      ],
      effectiveFrom: today().plusDays(-40),
    );
    final v = await s.view(a);
    await s.saveAnswers(
      a,
      v.answers.copyWith(
        duties: const [
          AgreementDuty(
            id: 'd1',
            title: 'Ijara haqini 5-sanagacha toʻlash',
            ownerPartyId: 'p1',
            breachClause: '3-band: 1 kun ichida xabar berasiz',
          ),
        ],
        custody: const CustodyRule(keeperPartyId: 'p1'),
      ),
    );
    await acc.reportDuty(
      a,
      dutyId: 'd1',
      partyId: 'p1',
      reason: 'Kasal boʻldim',
      fix: '2 kundan keyin toʻlayman',
    );
    await journal.append(
      a.meta.id,
      JournalDraft(
        kind: JournalKind.openingBalance,
        date: today(),
        partyId: 'p1',
        amount: Money.major(1000000, CurrencyCode.uzs),
      ),
    );
    final reviewId = await acc.openReview(a);
    await acc.acknowledge(
      a,
      reviewId: reviewId,
      partyId: 'p1',
      verdict: ReviewVerdict.agree,
    );
    await acc.acknowledge(
      a,
      reviewId: reviewId,
      partyId: 'p2',
      verdict: ReviewVerdict.object,
      objection: 'Kassa farqi 10 000 soʻm',
    );
    await acc.completeReview(a, reviewId: reviewId);
    final disputeId = await acc.openDispute(
      a,
      partyId: 'p2',
      topic: 'Ijara haqi',
      clause: '3-band',
      claim: 'Toʻlov kech boʻldi',
    );
    await acc.addDisputeClaim(
      a,
      disputeId: disputeId,
      partyId: 'p1',
      claim: 'Xabar berdim',
    );
    await acc.decideDispute(
      a,
      disputeId: disputeId,
      decision: 'Kechikish 3 kun',
    );
    return a;
  }

  test('hakam papkasi: barcha boʻlimlar bor (snapshot)', () async {
    final a = await withHistory();
    final v = await acc.view(a);
    final blocks = arbiterFolderBlocks(
      l: l,
      money: fmt,
      view: v.base,
      dispute: v.disputes.single,
      journal: v.base.journal,
    );
    final headings = [
      for (final b in blocks)
        if (b is PdfHeading) b.text,
    ];
    expect(headings, [
      l.acPdfFolderAgreement,
      l.acPdfFolderVersions,
      l.acPdfFolderParties,
      l.acPdfFolderLedger,
      l.acPdfFolderMinutes,
      l.acPdfFolderIncidents,
      l.acPdfFolderClaims,
      l.acPdfFolderDecision,
      l.acPdfFolderIntegrity,
    ]);
    final text = [
      for (final b in blocks)
        if (b is PdfParagraph) b.text,
      for (final b in blocks)
        if (b is PdfKeyValues) ...[for (final r in b.rows) r.$2],
    ].join('\n');
    expect(text, contains('Toʻlov kech boʻldi'), reason: 'talab');
    expect(text, contains('Kechikish 3 kun'), reason: 'hakam qarori');
    expect(text, contains('Kassa farqi 10 000 soʻm'), reason: "e'tiroz");
    expect(text, contains('Kasal boʻldim'), reason: 'vazifa hodisasi');
    expect(
      blocks.whereType<PdfTable>().any((t) => t.rows.isNotEmpty),
      isTrue,
      reason: 'yozuvlar jadvali',
    );
  });

  test("ko'rik bayonnomasi: davr yozuvlari, tomonlar va e'tiroz", () async {
    final a = await withHistory();
    final v = await acc.view(a);
    final blocks = reviewMinutesBlocks(
      l: l,
      money: fmt,
      answers: v.base.answers,
      journal: v.base.journal,
      minutes: v.minutes.single,
    );
    final headings = [
      for (final b in blocks)
        if (b is PdfHeading) b.text,
    ];
    expect(headings, [
      l.acReviewPeriodTitle,
      l.acReviewIncidents,
      l.acReviewAcksTitle,
    ]);
    final paragraphs = [
      for (final b in blocks)
        if (b is PdfParagraph) b.text,
    ];
    expect(paragraphs, contains(l.acReviewVerdictAgree('Akmal')));
    expect(
      paragraphs,
      contains(l.acReviewVerdictObject('Bahodir', 'Kassa farqi 10 000 soʻm')),
    );
  });

  test('PDF baytlari: hakam papkasi va bayonnoma haqiqiy PDF', () async {
    final a = await withHistory();
    final v = await acc.view(a);
    final fonts = await PdfFonts.load(rootBundle);
    final folder = await buildArbiterFolderPdf(
      fonts: fonts,
      l: l,
      money: fmt,
      view: v.base,
      dispute: v.disputes.single,
      journal: v.base.journal,
      footer: 'test',
    );
    final minutes = await buildReviewMinutesPdf(
      fonts: fonts,
      l: l,
      money: fmt,
      agreement: v.agreement,
      journal: v.base.journal,
      answers: v.base.answers,
      minutes: v.minutes.single,
      footer: 'test',
    );
    expect(String.fromCharCodes(folder.take(5)), '%PDF-');
    expect(String.fromCharCodes(minutes.take(5)), '%PDF-');
    expect(folder.length, greaterThan(1000));
  });
}
