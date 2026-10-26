import 'package:cryptography/dart.dart';

import 'hex.dart';

/// SHA-256, kichik harfli hex.
String sha256Hex(List<int> bytes) => hexEncode(const DartSha256().hashSync(bytes).bytes);
