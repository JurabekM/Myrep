import 'package:flutter_test/flutter_test.dart';
import 'package:zanjir_app/l10n/gen/app_localizations.dart';
import 'package:zanjir_app/l10n/labels.dart';
import 'package:zanjir_core/zanjir_core.dart';
import 'package:zanjir_data/zanjir_data.dart' show DataRuleException, ProtocolBlocker, ServerException, SyncRejected;

/// Baholovchi qaytaradigan barcha sabab kodlari (ADR-0005) tarjimaga ega.
const reasonCodes = [
  'out_of_limit',
  'value_missing',
  'invalid_value',
  'missing_ambient_temp',
  'test_voltage_below_norm',
  'no_pairs',
  'no_matching_norm',
  'norm_applicability_unknown',
  'loop_pair_not_pe',
  'unprotected_path',
  'no_protective_device',
  'fuse_protection',
  'device_attrs_missing',
  'curve_unknown',
  'zs_exceeded',
  'zs_exceeded_rcd_present',
  'zs_ambiguous_multiple_feeds',
  'rcd_multiplier_below_1',
  'rcd_not_tripped',
  'season_coeff_missing',
  'season_coeff_below_1',
  'no_upstream_rcd',
  'rcd_idn_missing',
  'factor_unavailable',
  'marked_not_applicable',
]; // fmt: skip

/// `ProtocolRepository.prepare` qaytaradigan barcha shartlar.
const blockerCodes = [
  'session_open',
  'no_measurements',
  'forbidden_role',
  'device_not_trusted',
  'license_missing',
  'license_expired',
  'already_signed',
  'instrument_expired',
  'mixed_norm_sets',
  'norms_not_reviewed',
  'needs_review_requires_lead',
  'lead_comment_required',
];

void main() {
  for (final locale in AppLocalizations.supportedLocales) {
    final l = lookupAppLocalizations(locale);
    test('${locale.languageCode}: sabablar, turlar, natijalar', () {
      for (final c in reasonCodes) {
        expect(l.reasonText(c), isNot(l.reasonOther(c)), reason: c);
      }
      expect(l.reasonText('yangi_kod'), l.reasonOther('yangi_kod'));
      for (final k in NodeKind.values) {
        expect(l.kindName(k), isNotEmpty);
      }
      for (final v in Verdict.values) {
        expect(l.verdictName(v), isNotEmpty);
      }
      for (final t in MeasurementType.values) {
        expect(l.typeName(t), isNotEmpty);
      }
      expect(l.disclaimer, isNot(contains('xavfsiz.')));
    });

    test('${locale.languageCode}: imzolash shartlari (ADR-0010)', () {
      for (final c in blockerCodes) {
        expect(l.blockerText(ProtocolBlocker(c, const ['id-1', 'id-2'])), isNot(l.blockerOther(c)), reason: c);
      }
      expect(l.blockerText(const ProtocolBlocker('instrument_expired', ['a', 'b', 'c'])), contains('3'));
      expect(l.blockerText(const ProtocolBlocker('forbidden_role', ['VIEWER'])), contains(l.roleViewer));
      expect(l.blockerText(const ProtocolBlocker('yangi')), l.blockerOther('yangi'));
      expect(l.errorText(const DataRuleException('draft_stale', 'changed')), l.errorDraftStale);
      expect(l.serverErrorText(const ServerException(422, 'push_rejected', reason: 'clock_skew')), l.errorClockSkew);
      expect(l.serverErrorText(const ServerException(429, 'too_many_attempts')), l.tooManyAttempts);
      // Qotgan yozuv ko'rsatiladi (M3, ADR-0014).
      final stuck = SyncRejected(
        const ServerException(422, 'push_rejected', reason: 'plan_immutable', opId: 'op'),
        table: 'isolation_plan',
        rowId: '0192aaaa-bbbb-7ccc-8ddd-eeeeffff0000',
      );
      expect(l.serverErrorText(stuck), l.syncRejectedRow('isolation_plan', '0192aaaa', 'plan_immutable'));
      expect(l.serverErrorText(const ServerException(0, 'timeout')), l.serverUnavailable);
    });
  }
}
