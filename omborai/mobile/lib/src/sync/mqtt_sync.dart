import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:mqtt_client/mqtt_client.dart';
import 'package:mqtt_client/mqtt_server_client.dart';

import 'crypto.dart';
import 'ops.dart';

/// MQTT transport (docs/sync-mqtt.md). Desktop bilan bir xil protokol.
///
/// [applyOp] — operatsiyani lokal bazaga qo'llaydi (dedupe bazada). [onRequest] — snapshot_request kelganda.
class MqttSync {
  MqttSync({
    required this.key,
    required this.deviceId,
    required this.applyOp,
    this.onRequest,
    this.host = 'broker.hivemq.com',
    this.port = 8883,
    this.secure = true,
  });

  final Uint8List key;
  final String deviceId;
  final Future<bool> Function(Map<String, dynamic> op) applyOp;
  void Function(Map<String, dynamic> request)? onRequest;
  final String host;
  final int port;
  final bool secure;

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
      ..logging(on: false);
    client.onConnected = () {
      _connected = true;
    };
    client.onDisconnected = () {
      _connected = false;
    };
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
    _client?.disconnect();
    _connected = false;
  }

  /// Operatsiyani shifrlab nashr qiladi. Ulanmagan bo'lsa StateError.
  Future<void> send(Map<String, dynamic> op) async {
    final client = _client;
    final topic = _topic;
    if (!_connected || client == null || topic == null) {
      throw StateError('MQTT broker bilan ulanmagan');
    }
    final envelope = await seal(key, op, topic);
    final builder = MqttClientPayloadBuilder()
      ..addString(utf8.decode(envelope));
    client.publishMessage(topic, MqttQos.atLeastOnce, builder.payload!);
  }

  Future<void> _onMessage(Uint8List raw) async {
    final topic = _topic;
    if (topic == null) return;
    final Map<String, dynamic> op;
    try {
      op = await openEnvelope(key, raw, topic);
    } on DecryptionException {
      return; // boshqa kalit yoki buzilgan xabar
    }
    if (op['device'] == deviceId) return; // o'z xabarimiz allaqachon qo'llangan
    if (op['type'] == opSnapshotRequest) {
      onRequest?.call(op);
      return;
    }
    await applyOp(op);
  }
}
