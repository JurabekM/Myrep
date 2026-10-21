import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

/// Yadro bergan fayl baytlarini (PDF, `.baraka`) ulashish oynasi orqali saqlash yoki yuborish.
/// Fayl vaqtinchalik papkaga yoziladi; ulashilgandan keyin keshda qoladi va tizim tozalaydi.
typedef ShareFile = Future<void> Function(Uint8List bytes, String name, String mime);

Future<void> shareFile(Uint8List bytes, String name, String mime) async {
  final dir = await getTemporaryDirectory();
  final file = File('${dir.path}/$name');
  await file.writeAsBytes(bytes, flush: true);
  await SharePlus.instance.share(
    ShareParams(
      files: [XFile(file.path, mimeType: mime)],
      fileNameOverrides: [name],
    ),
  );
}

/// Testlarda almashtiriladi (ulashilgan fayllar ro'yxatga yoziladi).
final shareFileProvider = Provider<ShareFile>((ref) => shareFile);

const pdfMime = 'application/pdf';
