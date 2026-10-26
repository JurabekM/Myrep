// Xavfsizlik uchun muhim kod (evaluator, solver, kanonik JSON) — 100% qator va branch coverage.
// Foydalanish: dart run coverage:test_with_coverage --branch-coverage && dart run tool/check_coverage.dart
import 'dart:io';

const _required = ['lib/src/eval/', 'lib/src/solver/', 'lib/src/crypto/'];

void main(List<String> args) {
  final lcov = File(args.isEmpty ? 'coverage/lcov.info' : args.first);
  if (!lcov.existsSync()) {
    stderr.writeln('${lcov.path} topilmadi — avval test_with_coverage --branch-coverage');
    exit(2);
  }
  String? file;
  final missedLines = <String, List<int>>{};
  final missedBranches = <String, List<int>>{};
  final seen = <String>{};
  var branchRecords = 0;
  for (final line in lcov.readAsLinesSync()) {
    if (line.startsWith('SF:')) {
      final path = line.substring(3).replaceAll(r'\', '/');
      final i = path.lastIndexOf('/lib/');
      file = i >= 0 ? path.substring(i + 1) : path;
      if (!_required.any(file.startsWith)) file = null;
      if (file != null) seen.add(file);
    } else if (file != null && line.startsWith('DA:')) {
      final p = line.substring(3).split(',');
      if (p[1] == '0') missedLines.putIfAbsent(file, () => []).add(int.parse(p[0]));
    } else if (file != null && line.startsWith('BRDA:')) {
      branchRecords++;
      final p = line.substring(5).split(',');
      if (p[3] == '-' || p[3] == '0') missedBranches.putIfAbsent(file, () => []).add(int.parse(p[0]));
    }
  }
  if (seen.isEmpty || branchRecords == 0) {
    stderr.writeln('Tekshiriladigan fayllar yoki branch ma\'lumotlari topilmadi (--branch-coverage?)');
    exit(2);
  }
  var ok = true;
  for (final f in seen.toList()..sort()) {
    final l = missedLines[f] ?? const [];
    final b = missedBranches[f] ?? const [];
    if (l.isEmpty && b.isEmpty) continue;
    ok = false;
    stderr.writeln('$f: qoplanmagan qatorlar $l, branchlar (qator) $b');
  }
  if (!ok) exit(1);
  stdout.writeln(
    'Evaluator/solver/crypto: ${seen.length} fayl, 100% qator va branch coverage ($branchRecords branch).',
  );
}
