import 'package:uuid/uuid.dart';

import 'crypto.dart';
import 'identity.dart';

/// Operatsiya turlari va ruxsatlar (docs/sync-mqtt.md, 6-bo'lim). Desktop `sync/ops.py` bilan bir xil.
const opDevice = 'device';
const opJoinRequest = 'join_request';
const opStore = 'store';
const opUser = 'user';
const opProduct = 'product';
const opMovement = 'movement';
const opSale = 'sale';
const opShiftOpen = 'shift_open';
const opShiftClose = 'shift_close';
const opRefund = 'refund';
const opSnapshot = 'snapshot';
const opSnapshotRequest = 'snapshot_request';

const roleOwner = 'owner';
const roleCashier = 'cashier';

/// Faqat egasi qurilmasi imzolaydi.
const ownerOnlyTypes = {
  opDevice,
  opStore,
  opUser,
  opProduct,
  opMovement,
  opRefund,
  opSnapshot,
};

const knownTypes = {
  ...ownerOnlyTypes,
  opJoinRequest,
  opSale,
  opShiftOpen,
  opShiftClose,
  opSnapshotRequest,
};

const movementKinds = {'receipt', 'adjustment', 'writeoff'};

/// Natijalar (LocalDb.applyOp): qo'llandi, takror, rad etildi, kutiladi, qo'llanmadi (xato emas).
const resultApplied = 'applied';
const resultDuplicate = 'duplicate';
const resultRejected = 'rejected';
const resultPending = 'pending';
const resultSkipped = 'skipped';

const _uuid = Uuid();

/// UTC, aniq 6 ta kasr raqamli vaqt: YYYY-MM-DDTHH:MM:SS.ffffffZ (satr bo'yicha solishtiriladi).
String nowTs([DateTime? at]) {
  final t = (at ?? DateTime.now()).toUtc();
  String p(int n, [int width = 2]) => n.toString().padLeft(width, '0');
  return '${p(t.year, 4)}-${p(t.month)}-${p(t.day)}T${p(t.hour)}:${p(t.minute)}:'
      '${p(t.second)}.${p(t.millisecond, 3)}${p(t.microsecond, 3)}Z';
}

/// Imzosiz operatsiya tuzilishi. Imzo [signedOp] da qo'yiladi.
Map<String, dynamic> rawOp({
  required String type,
  required String storeId,
  required Map<String, dynamic> payload,
  required String deviceId,
  String? opId,
  String? ts,
}) {
  return {
    'op_id': opId ?? _uuid.v4(),
    'type': type,
    'device': deviceId,
    'ts': ts ?? nowTs(),
    'store_id': storeId,
    'payload': payload,
  };
}

/// Shu qurilma nomidan imzolangan operatsiya.
Future<Map<String, dynamic>> signedOp(
  DeviceIdentity identity, {
  required String type,
  required String storeId,
  required Map<String, dynamic> payload,
  required String deviceId,
  String? opId,
  String? ts,
}) async {
  final op = rawOp(
    type: type,
    storeId: storeId,
    payload: payload,
    deviceId: deviceId,
    opId: opId,
    ts: ts,
  );
  await signOp(op, identity.keyPair);
  return op;
}

/// Bir chek faqat bir marta qaytariladi: barcha qurilmalarda bir xil op_id.
String refundOpId(String saleId) => 'refund:$saleId';
