/// Domen enumlari. `code` — baza, YAML va JSON'dagi qiymat.
library;

T _parse<T extends Enum>(List<T> values, String code, String Function(T) codeOf, String what) {
  for (final v in values) {
    if (codeOf(v) == code) return v;
  }
  throw FormatException('Noma\'lum $what: $code');
}

enum NodeKind {
  srcGrid('SRC_GRID'),
  srcTransformer('SRC_TRANSFORMER'),
  srcGenerator('SRC_GENERATOR'),
  srcPvInverter('SRC_PV_INVERTER'),
  srcUps('SRC_UPS'),
  srcBattery('SRC_BATTERY'),
  srcCapacitor('SRC_CAPACITOR'),
  breaker('BREAKER'),
  rcd('RCD'),
  rcbo('RCBO'),
  fuse('FUSE'),
  loadSwitch('SWITCH'),
  ats('ATS'),
  contactor('CONTACTOR'),
  busbar('BUSBAR'),
  panel('PANEL'),
  cable('CABLE'),
  load('LOAD'),
  socketGroup('SOCKET_GROUP'),
  earthElectrode('EARTH_ELECTRODE'),
  peBar('PE_BAR');

  const NodeKind(this.code);
  final String code;

  /// `SRC_*` — manbalar (teskari ta'minot manbalari ham).
  bool get isSource => index <= srcCapacitor.index;

  /// Kommutatsiya apparatlari (`state` faqat ularda bo'ladi).
  bool get isSwitching => index >= breaker.index && index <= contactor.index;

  static NodeKind parse(String code) => _parse(values, code, (v) => v.code, 'node.kind');
}

enum EarthingSystem {
  tnC('TN-C'),
  tnS('TN-S'),
  tnCS('TN-C-S'),
  tt('TT'),
  it('IT');

  const EarthingSystem(this.code);
  final String code;

  static EarthingSystem parse(String code) => _parse(values, code, (v) => v.code, 'earthing_system');
}

enum MeasurementType {
  insulation('INSULATION'),
  loopImpedance('LOOP_IMPEDANCE'),
  rcdTrip('RCD_TRIP'),
  earthResistance('EARTH_RESISTANCE'),
  continuityBonding('CONTINUITY_BONDING');

  const MeasurementType(this.code);
  final String code;

  static MeasurementType parse(String code) => _parse(values, code, (v) => v.code, 'measurement_type');
}

/// Baholash natijasi. PASS hech qachon standart qiymat emas (CLAUDE.md, 3-qoida).
enum Verdict {
  pass('PASS'),
  fail('FAIL'),
  needsReview('NEEDS_REVIEW'),
  notApplicable('NOT_APPLICABLE');

  const Verdict(this.code);
  final String code;
}

enum SessionKind {
  qabulTopshirish('QABUL_TOPSHIRISH'),
  davriy('DAVRIY'),
  navbatdanTashqari('NAVBATDAN_TASHQARI');

  const SessionKind(this.code);
  final String code;
}

enum EnteredVia {
  manual('MANUAL'),
  ocr('OCR'),
  bt('BT');

  const EnteredVia(this.code);
  final String code;
}

enum SwitchState {
  closed('CLOSED'),
  open('OPEN');

  const SwitchState(this.code);
  final String code;
}
