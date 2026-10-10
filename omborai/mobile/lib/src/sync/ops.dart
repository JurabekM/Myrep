import 'package:uuid/uuid.dart';

/// Operatsiya turlari (docs/sync-mqtt.md). Desktop bilan bir xil.
const opSale = 'sale';
const opRefund = 'refund';
const opShiftOpen = 'shift_open';
const opShiftClose = 'shift_close';
const opMovement = 'movement';
const opProduct = 'product';
const opUser = 'user';
const opStore = 'store';
const opSnapshot = 'snapshot';
const opSnapshotRequest = 'snapshot_request';

const _uuid = Uuid();

Map<String, dynamic> newOp({
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
    'ts': ts ?? DateTime.now().toUtc().toIso8601String(),
    'store_id': storeId,
    'payload': payload,
  };
}

/// Bir chek faqat bir marta qaytariladi: barcha qurilmalarda bir xil op_id.
String refundOpId(String saleId) => 'refund:$saleId';
