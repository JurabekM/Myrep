import 'dart:convert';
import 'dart:io';

import 'package:baraka_daftari/core/security/integrity/integrity_service.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../helpers/fakes.dart';

void main() {
  late Directory dir;

  setUp(() => dir = Directory.systemTemp.createTempSync('baraka_integrity'));
  tearDown(() => dir.deleteSync(recursive: true));

  test('faqat vaqt va xavf kodlari yoziladi', () async {
    final clock = FakeClock();
    final log = IntegrityLog(() async => dir, clock);
    await log.append({IntegrityRisk.rooted, IntegrityRisk.emulator});

    final lines = await log.readLines();
    final entry = jsonDecode(lines.single) as Map<String, dynamic>;
    expect(entry.keys, unorderedEquals(['ts', 'risks']));
    expect(entry['risks'], ['rooted', 'emulator']);
    expect(entry['ts'], clock.nowUtc().toIso8601String());
    expect(File('${dir.path}/security/integrity.log').existsSync(), isTrue);
  });

  test('log ${IntegrityLog.maxLines} qatordan oshmaydi', () async {
    final clock = FakeClock();
    final log = IntegrityLog(() async => dir, clock);
    for (var i = 0; i < IntegrityLog.maxLines + 5; i++) {
      clock.advance(const Duration(minutes: 1));
      await log.append({IntegrityRisk.debugger});
    }
    final lines = await log.readLines();
    expect(lines, hasLength(IntegrityLog.maxLines));
    expect(
      (jsonDecode(lines.last) as Map<String, dynamic>)['ts'],
      clock.nowUtc().toIso8601String(),
    );
  });
}
