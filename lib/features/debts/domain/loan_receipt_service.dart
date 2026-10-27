import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/debts/domain/debts.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';

/// Qarz tilxati (`LoanReceipt`, SPEC 2D.5): tomonlar va guvohlar shu
/// qurilmada ismini yozib, ekranda imzo chizadi.
class LoanReceiptService {
  LoanReceiptService({
    required HouseholdRepository households,
    required LoanSignerRepository signers,
    required SyncMetaFactory metaFactory,
    required Clock clock,
  }) : _households = households,
       _signers = signers,
       _meta = metaFactory,
       _clock = clock;

  static const errNameRequired = 'signer_name_required';
  static const errEmptySignature = 'signature_empty';

  final HouseholdRepository _households;
  final LoanSignerRepository _signers;
  final SyncMetaFactory _meta;
  final Clock _clock;

  /// Hujjat imzolovchilari; birinchi ochilishda tomonlar ([borrower],
  /// [lender]) yaratiladi.
  Future<List<LoanSigner>> signers(
    String documentId, {
    required String borrower,
    required String lender,
  }) async {
    final existing = await _signers.forDocument(documentId);
    if (existing.isNotEmpty) return existing;
    final hh = (await _households.current()).meta.id;
    for (final (role, name) in [
      (SignerRole.lender, lender),
      (SignerRole.borrower, borrower),
    ]) {
      await _signers.add(
        LoanSigner(
          meta: _meta.create(hh),
          documentId: documentId,
          role: role,
          name: name,
        ),
      );
    }
    return _signers.forDocument(documentId);
  }

  /// Imzo: ismni tasdiqlab (o'zgartirish mumkin) ekranda chizilgan PNG.
  Future<LoanSigner> sign(LoanSigner s, String name, List<int> png) async {
    if (name.trim().isEmpty) throw const DomainRuleException(errNameRequired);
    if (png.isEmpty) throw const DomainRuleException(errEmptySignature);
    return _signers.update(
      s.copyWith(
        name: name.trim(),
        signaturePng: png,
        signedAt: _clock.nowUtc(),
      ),
    );
  }
}
