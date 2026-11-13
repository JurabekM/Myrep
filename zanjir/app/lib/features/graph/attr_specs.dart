import 'package:zanjir_core/zanjir_core.dart';

import '../../l10n/gen/app_localizations.dart';

enum AttrType { number, text, choice, flag }

/// Tugun atributi tavsifi (prompt 4-bo'lim `node.attrs` va ADR-0002/0005 dagi tanlov atributlari).
class AttrSpec {
  const AttrSpec(this.key, this.type, [this.options = const []]);
  final String key;
  final AttrType type;
  final List<String> options;

  String label(AppLocalizations l) => switch (key) {
    'in_a' => l.attrInA,
    'curve' => l.attrCurve,
    'idn_ma' => l.attrIdnMa,
    'rcd_type' => l.attrRcdType,
    'selective' => l.attrSelective,
    'cores' => l.attrCores,
    'csa_mm2' => l.attrCsaMm2,
    'material' => l.attrMaterial,
    'length_m' => l.attrLengthM,
    'circuit_role' => l.attrCircuitRole,
    'circuit_class' => l.attrCircuitClass,
    'role' => l.attrRole,
    'anti_islanding' => l.attrAntiIslanding,
    _ => key,
  };

  String optionLabel(AppLocalizations l, String v) => switch ((key, v)) {
    ('circuit_role', 'final') => l.circuitRoleFinal,
    ('circuit_role', 'distribution') => l.circuitRoleDistribution,
    ('circuit_class', 'wiring') => l.circuitClassWiring,
    ('circuit_class', 'power') => l.circuitClassPower,
    ('circuit_class', 'secondary') => l.circuitClassSecondary,
    ('role', 'neutral') => l.electrodeNeutral,
    ('role', 'repeat') => l.electrodeRepeat,
    ('role', 'tt') => l.electrodeTt,
    _ => v,
  };
}

const _inA = AttrSpec('in_a', AttrType.number);
const _curve = AttrSpec('curve', AttrType.choice, ['B', 'C', 'D']);
const _idn = AttrSpec('idn_ma', AttrType.number);
const _rcdType = AttrSpec('rcd_type', AttrType.choice, ['AC', 'A', 'F', 'B']);
const _selective = AttrSpec('selective', AttrType.flag);
const _circuitRole = AttrSpec('circuit_role', AttrType.choice, ['final', 'distribution']);

List<AttrSpec> attrSpecsFor(NodeKind k) => switch (k) {
  NodeKind.breaker => const [_inA, _curve],
  NodeKind.rcd => const [_inA, _idn, _rcdType, _selective],
  NodeKind.rcbo => const [_inA, _curve, _idn, _rcdType, _selective],
  NodeKind.fuse => const [_inA],
  NodeKind.cable => const [
    AttrSpec('cores', AttrType.number),
    AttrSpec('csa_mm2', AttrType.number),
    AttrSpec('material', AttrType.choice, ['Cu', 'Al']),
    AttrSpec('length_m', AttrType.number),
    AttrSpec('circuit_class', AttrType.choice, ['wiring', 'power', 'secondary']),
    _circuitRole,
  ],
  NodeKind.load || NodeKind.socketGroup || NodeKind.panel || NodeKind.busbar => const [_circuitRole],
  NodeKind.earthElectrode => const [
    AttrSpec('role', AttrType.choice, ['neutral', 'repeat', 'tt']),
  ],
  NodeKind.srcPvInverter => const [AttrSpec('anti_islanding', AttrType.flag)],
  _ => const [],
};
