import '../model/enums.dart';

/// Kesish narxlari (prompt 5.3, 3-band). Ro'yxatda yo'q tugunlar va zona tugunlari kesilmaydi (∞).
/// O'zgartirish — `solverVersion` ni oshirish bilan.
const Map<NodeKind, int> cutCosts = {
  NodeKind.loadSwitch: 1,
  NodeKind.fuse: 2,
  NodeKind.breaker: 3,
  NodeKind.rcbo: 3,
  NodeKind.rcd: 5,
  NodeKind.contactor: 50,
  NodeKind.ats: 50,
};

/// Kesimga tushsa ogohlantirish beriladigan apparatlar (masofadan/avtomatik yoqilishi mumkin).
const Set<NodeKind> warnInCut = {NodeKind.contactor, NodeKind.ats};
