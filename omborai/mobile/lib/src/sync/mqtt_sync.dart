import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:mqtt_client/mqtt_client.dart';
import 'package:mqtt_client/mqtt_server_client.dart';

import 'crypto.dart';
import 'ops.dart';

/// MQTT transport (protokol v2, docs/sync-mqtt.md, 8-bo'lim). Desktop `mqtt_sync.py` bilan bir xil.
///
/// - Sessiya persistent (`clean start` yo'q): ulanish uzilganda broker xabarlarni saqlaydi.
/// - [send] PUBACK kelguncha kutadi: chaqiruvchi navbatdan faqat shundan keyin o'chiradi (K4).
/// - Xabarni qayta ishlash xatolari ushlanadi: qabul oqimi o'lmaydi (Y2).
class MqttSync {
  MqttSync({
    required this.key,
    required this.deviceId,
    required this.applyOp,
    this.onRequest,
    this.onJoinRequest,
    this.host = 'broker.hivemq.com',
    this.port = 8883,
    this.secure = true,
    this.ackTimeout = const Duration(seconds: 10),
  });

  final Uint8List key;
  final String deviceId;

  /// Operatsiyani qo'llaydi (LocalDb.applyOp). Natija: resultApplied, resultRejected, ...
  final Future<String> Function(Map<String, dynamic> op) applyOp;

  /// snapshot_request kelganda (faqat egasi qurilmasi javob beradi).
  void Function(Map<String, dynamic> request)? onRequest;

  /// join_request kelganda (egasi tasdig'i uchun).
  void Function(Map<String, dynamic> request)? onJoinRequest;

  final String host;
  final int port;
  final bool secure;
  final Duration ackTimeout;

  MqttServerClient? _client;
  StreamSubscription<dynamic>? _updates;
  String? _topic;
  bool _connected = false;

  bool get connected => _connected;

  Future<void> start() async {
    final topic = await topicFor(key);
    _topic = topic;
    final client = MqttServerClient.withPort(host, 'omborai-$deviceId', port)
      ..secure = secure
      ..keepAlivePeriod = 30
      ..autoReconnect = true
      ..resubscribeOnAutoReconnect = true
      ..logging(on: false)
      // Persistent sessiya: startClean() chaqirilmaydi (mqtt_client default'i clean start)
      ..connectionMessage = MqttConnectMessage().withClientIdentifier('omborai-$deviceId');
    client.onConnected = () => _connected = true;
    client.onDisconnected = () => _connected = false;
    if (secure) client.securityContext = SecurityContext.defaultContext;
    _client = client;

    await client.connect();
    if (client.connectionStatus?.state != MqttConnectionState.connected) {
      throw StateError('MQTT ulanmadi: ${client.connectionStatus?.returnCode}');
    }
    _connected = true;
    client.subscribe(topic, MqttQos.atLeastOnce);
    _updates = client.updates?.listen((messages) {
      for (final message in messages) {
        final publish = message.payload;
        if (publish is MqttPublishMessage) {
          unawaited(_onMessage(Uint8List.fromList(publish.payload.message)));
        }
      }
    });
  }

  Future<void> stop() async {
    await _updates?.cancel();
    _updates = null;
    _client?.disconnect();
    _connected = false;
  }

  /// Operatsiyani shifrlab nashr qiladi va broker PUBACK'ini kutadi. Ulanmagan bo'lsa StateError.
  Future<void> send(Map<String, dynamic> op) async {
    final client = _client;
    final topic = _topic;
    if (!_connected || client == null || topic == null) {
      throw StateError('MQTT broker bilan ulanmagan');
    }
    final envelope = await seal(key, op, topic);
    final builder = MqttClientPayloadBuilder()..addString(utf8.decode(envelope));
    // PUBACK oqimi nashrdan OLDIN tinglanishi kerak: mqtt_client faqat tinglovchi bo'lsa xabar beradi
    final acked = Completer<void>();
    int? messageId;
    final subscription = client.published!.listen((message) {
      if (messageId != null && message.variableHeader?.messageIdentifier == messageId) {
        if (!acked.isCompleted) acked.complete();
      }
    });
    try {
      messageId = client.publishMessage(topic, MqttQos.atLeastOnce, builder.payload!);
      await acked.future.timeout(ackTimeout);
    } on TimeoutException {
      throw StateError('PUBACK kelmadi: broker tasdiqlamadi');
    } finally {
      await subscription.cancel();
    }
  }

  Future<void> _onMessage(Uint8List raw) async {
    try {
      final topic = _topic;
      if (topic == null) return;
      final Map<String, dynamic> op;
      try {
        op = await openEnvelope(key, raw, topic);
      } on DecryptionException {
        return; // boshqa kalit yoki buzilgan xabar
      }
      if (op['device'] == deviceId) return; // o'z xabarimiz allaqachon qo'llangan
      switch (op['type']) {
        case opSnapshotRequest:
          onRequest?.call(op);
        case opJoinRequest:
          onJoinRequest?.call(op);
        default:
          await applyOp(op);
      }
    } on Object {
      // Xato ilovani to'xtatmasin: keyingi xabarlar qayta ishlanadi
    }
  }
}
