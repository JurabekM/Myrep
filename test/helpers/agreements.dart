import 'package:baraka_daftari/features/agreements/data/agreement_providers.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement_service.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Bog'langan kelishuvning foydalanuvchi to'ldiradigan savollari (3, 6, 7,
/// 8): har tomonga vazifa va «bajarilmasa» bandi, hisob, chiqish, hakam —
/// imzolash 9/9 dan keyin ochiladi (Vazifa 9A).
Future<AgreementView> completeAgreement(
  AgreementService s,
  AgreementSource source,
  String sourceId, {
  String arbiter = 'Shavkat aka',
}) async {
  final a = (await s.bySource(source, sourceId))!;
  final v = await s.view(a);
  final ans = v.answers;
  return s.saveAnswers(
    a,
    ans.copyWith(
      duties: a.type == AgreementType.loan
          ? ans.duties
          : [
              for (final (i, p) in ans.parties.indexed)
                AgreementDuty(
                  id: 'd$i',
                  title: 'Vazifa ${i + 1}',
                  ownerPartyId: p.id,
                  breachClause: '1 kun ichida xabar beradi',
                ),
            ],
      custody: CustodyRule(
        where: 'Umumiy karta',
        keeperPartyId: ans.parties.first.id,
      ),
      exit: ExitClause(
        valuation: 'Oxirgi koʻrik boʻyicha',
        payout: ans.exit.payout.isEmpty ? '3 oy ichida' : ans.exit.payout,
      ),
      arbiter: ArbiterInfo(name: arbiter, role: 'oqsoqol'),
    ),
  );
}

/// [completeAgreement] — provayderlar orqali.
Future<AgreementView> completeAgreementIn(
  ProviderContainer c,
  AgreementSource source,
  String sourceId,
) async => completeAgreement(
  await c.read(agreementServiceProvider.future),
  source,
  sourceId,
);
