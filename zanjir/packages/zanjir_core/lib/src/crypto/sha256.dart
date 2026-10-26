import 'package:cryptography/dart.dart';

/// SHA-256, kichik harfli hex.
String sha256Hex(List<int> bytes) =>
    const DartSha256().hashSync(bytes).bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
