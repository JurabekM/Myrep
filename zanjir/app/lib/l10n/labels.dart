import 'package:zanjir_core/zanjir_core.dart';
import 'package:zanjir_data/zanjir_data.dart' show DataRuleException, ProtocolBlocker, ServerException;

import 'gen/app_localizations.dart';

/// Domen kodlari → lokalizatsiya qilingan matn (UI'da qattiq yozilgan matn yo'q).
extension Labels on AppLocalizations {
  String kindName(NodeKind k) => switch (k) {
    NodeKind.srcGrid => kindSrcGrid,
    NodeKind.srcTransformer => kindSrcTransformer,
    NodeKind.srcGenerator => kindSrcGenerator,
    NodeKind.srcPvInverter => kindSrcPvInverter,
    NodeKind.srcUps => kindSrcUps,
    NodeKind.srcBattery => kindSrcBattery,
    NodeKind.srcCapacitor => kindSrcCapacitor,
    NodeKind.breaker => kindBreaker,
    NodeKind.rcd => kindRcd,
    NodeKind.rcbo => kindRcbo,
    NodeKind.fuse => kindFuse,
    NodeKind.loadSwitch => kindSwitch,
    NodeKind.ats => kindAts,
    NodeKind.contactor => kindContactor,
    NodeKind.busbar => kindBusbar,
    NodeKind.panel => kindPanel,
    NodeKind.cable => kindCable,
    NodeKind.load => kindLoad,
    NodeKind.socketGroup => kindSocketGroup,
    NodeKind.earthElectrode => kindEarthElectrode,
    NodeKind.peBar => kindPeBar,
  };

  String verdictName(Verdict v) => switch (v) {
    Verdict.pass => verdictPass,
    Verdict.fail => verdictFail,
    Verdict.needsReview => verdictNeedsReview,
    Verdict.notApplicable => verdictNotApplicable,
  };

  String typeName(MeasurementType t) => switch (t) {
    MeasurementType.insulation => typeInsulation,
    MeasurementType.loopImpedance => typeLoop,
    MeasurementType.rcdTrip => typeRcd,
    MeasurementType.earthResistance => typeEarth,
    MeasurementType.continuityBonding => typeBonding,
  };

  String sessionKindName(SessionKind k) => switch (k) {
    SessionKind.qabulTopshirish => sessionKindQabul,
    SessionKind.davriy => sessionKindDavriy,
    SessionKind.navbatdanTashqari => sessionKindNavbatdan,
  };

  String planStatusName(String status) => switch (status) {
    'DRAFT' => planStatusDraft,
    'APPROVED' => planStatusApproved,
    'EXECUTED' => planStatusExecuted,
    'CANCELLED' => planStatusCancelled,
    'STALE' => planStatusStale,
    _ => status,
  };

  String roleName(String role) => switch (role) {
    'ADMIN' => roleAdmin,
    'LEAD' => roleLead,
    'ENGINEER' => roleEngineer,
    _ => roleViewer,
  };

  /// `eval_detail.reason` kodlari (ADR-0005).
  String reasonText(String? code) => switch (code) {
    'out_of_limit' => reasonOutOfLimit,
    'zs_exceeded' => reasonZsExceeded,
    'value_missing' => reasonValueMissing,
    'invalid_value' => reasonInvalidValue,
    'missing_ambient_temp' => reasonMissingAmbientTemp,
    'test_voltage_below_norm' => reasonTestVoltageBelowNorm,
    'no_pairs' => reasonNoPairs,
    'no_matching_norm' => reasonNoMatchingNorm,
    'norm_applicability_unknown' => reasonNormApplicabilityUnknown,
    'loop_pair_not_pe' => reasonLoopPairNotPe,
    'unprotected_path' => reasonUnprotectedPath,
    'no_protective_device' => reasonNoProtectiveDevice,
    'fuse_protection' => reasonFuseProtection,
    'device_attrs_missing' => reasonDeviceAttrsMissing,
    'curve_unknown' => reasonCurveUnknown,
    'zs_exceeded_rcd_present' => reasonZsExceededRcdPresent,
    'zs_ambiguous_multiple_feeds' => reasonZsAmbiguous,
    'rcd_multiplier_below_1' => reasonRcdMultiplierBelow1,
    'rcd_not_tripped' => reasonRcdNotTripped,
    'season_coeff_missing' => reasonSeasonCoeffMissing,
    'season_coeff_below_1' => reasonSeasonCoeffBelow1,
    'no_upstream_rcd' => reasonNoUpstreamRcd,
    'rcd_idn_missing' => reasonRcdIdnMissing,
    'factor_unavailable' => reasonFactorUnavailable,
    'marked_not_applicable' => reasonMarkedNotApplicable,
    _ => reasonOther(code ?? '—'),
  };

  /// Reja qadami matni; `labelOf` — tugun ID → yorliq.
  String stepText(PlanStep s, String Function(String id) labelOf) {
    final label = s.nodeIds.isEmpty ? '' : labelOf(s.nodeIds.first);
    return switch (s.kind) {
      StepKind.stopPvAc => stepStopPvAc(label),
      StepKind.stopPvDc => stepStopPvDc(label),
      StepKind.stopGenerator => stepStopGenerator(label),
      StepKind.stopUps => stepStopUps(label),
      StepKind.stopBattery => stepStopBattery(label),
      StepKind.openDevice => s.params['action'] == 'REMOVE_FUSE' ? stepRemoveFuse(label) : stepOpenDevice(label),
      StepKind.lockAndTag => stepLockAndTag(label),
      StepKind.verifyNoVoltage => stepVerifyNoVoltage(_entry(s, labelOf)),
      StepKind.applyEarthing => stepApplyEarthing(_entry(s, labelOf)),
      StepKind.fenceAndSign => stepFenceAndSign,
    };
  }

  String _entry(PlanStep s, String Function(String id) labelOf) {
    final zone = labelOf(s.params['zone_node_id']! as String);
    final outside = s.params['outside_node_id'] as String?;
    return outside == null ? zone : '$zone ← ${labelOf(outside)}';
  }

  String warningText(PlanWarning w, String Function(String id) labelOf) {
    final labels = w.nodeIds.map(labelOf).join(', ');
    return switch (w.kind) {
      WarningKind.unverifiedNode => warnUnverifiedNode(labels),
      WarningKind.capacitorInZone => warnCapacitorInZone(labels),
      WarningKind.cableDischarge => warnCableDischarge(labels),
      WarningKind.pvDcSide => warnPvDcSide(labels),
      WarningKind.penConductor => warnPenConductor,
      WarningKind.contactorOrAtsInCut => warnContactorOrAts(labels),
      WarningKind.noSourceReachable => warnNoSourceReachable,
      WarningKind.earthingSystemUnknown => warnEarthingUnknown,
    };
  }

  /// Imzolashni to'xtatuvchi shart (ADR-0010).
  String blockerText(ProtocolBlocker b) => switch (b.code) {
    'session_open' => blockerSessionOpen,
    'no_measurements' => blockerNoMeasurements,
    'forbidden_role' => blockerForbiddenRole(roleName(b.ids.firstOrNull ?? '')),
    'device_not_trusted' => blockerDeviceNotTrusted,
    'license_missing' => blockerLicenseMissing,
    'license_expired' => blockerLicenseExpired,
    'already_signed' => blockerAlreadySigned,
    'instrument_expired' => blockerInstrumentExpired(b.ids.length),
    'mixed_norm_sets' => blockerMixedNormSets(b.ids.join(', ')),
    'norms_not_reviewed' => blockerNormsNotReviewed(b.ids.join(', ')),
    'needs_review_requires_lead' => blockerNeedsReviewLead(b.ids.length),
    'lead_comment_required' => blockerLeadComment(b.ids.length),
    _ => blockerOther(b.code),
  };

  /// Server va sinxronlash xatolari (ADR-0012).
  String serverErrorText(Object e) => switch (e) {
    ServerException(unavailable: true) => serverUnavailable,
    ServerException(code: 'invalid_credentials') => invalidCredentials,
    ServerException(code: 'invalid_invite') => invalidInvite,
    ServerException(code: 'conflict') => phoneTaken,
    ServerException(code: 'invalid_phone') => invalidPhone,
    ServerException(code: 'session_expired' || 'not_authenticated' || 'invalid_token') => sessionExpired,
    ServerException(code: 'push_rejected', :final reason) => syncRejected(reason ?? '—'),
    ServerException(:final code) => serverError(code),
    StateError(message: 'profile_mismatch' || 'profile_exists') => profileMismatch,
    _ => errorText(e),
  };

  /// Repozitoriy xatolari foydalanuvchiga.
  String errorText(Object e) => switch (e) {
    final DataRuleException d when d.code == 'forbidden_role' => errorForbidden,
    final DataRuleException d when d.code == 'session_closed' => errorSessionClosed,
    final DataRuleException d when d.code == 'invalid_k_corr' => invalidKCorr,
    final DataRuleException d when d.code == 'invalid_margin' => invalidMargin,
    final DataRuleException d when d.code == 'draft_stale' => errorDraftStale,
    final DataRuleException d when d.code == 'plan_stale' => errorPlanStale,
    final DataRuleException d when d.code == 'out_of_order' => errorStepOrder,
    final DataRuleException d when d.code == 'steps_incomplete' => errorStepsIncomplete,
    final DataRuleException d
        when const {
          'confirmation_required',
          'indicator_pretest_required',
          'no_voltage_confirmation_required',
        }.contains(d.code) =>
      errorStepConfirmation,
    final DataRuleException d => actionError(d.code),
    _ => actionError('$e'),
  };
}

/// Tugun turiga mos standart o'lchov turi.
MeasurementType defaultMeasurementType(NodeKind k) => switch (k) {
  NodeKind.rcd || NodeKind.rcbo => MeasurementType.rcdTrip,
  NodeKind.earthElectrode => MeasurementType.earthResistance,
  NodeKind.peBar => MeasurementType.continuityBonding,
  NodeKind.socketGroup || NodeKind.load || NodeKind.breaker || NodeKind.fuse => MeasurementType.loopImpedance,
  _ => MeasurementType.insulation,
};
