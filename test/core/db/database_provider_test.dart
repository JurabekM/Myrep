import 'dart:io';
import 'dart:typed_data';

import 'package:baraka_daftari/core/db/database_provider.dart';
import 'package:baraka_daftari/core/security/security_bridge.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import '../../helpers/pump_app.dart' show MockSecurityApi;

void main() {
  // Regressiya: qurilmada platforma kanali kalitni oʻzgarmas koʻrinishda
  // qaytaradi va provayder uni tozalashda yiqilib, baza umuman ochilmasdi.
  test(
    'platformadan oʻzgarmas kalit kelsa ham baza provayderi ishlaydi',
    () async {
      final dir = await Directory.systemTemp.createTemp('baraka_db');
      addTearDown(() => dir.delete(recursive: true));
      final api = MockSecurityApi();
      final original = Uint8List.fromList(List<int>.generate(32, (i) => i + 1));
      when(api.getOrCreateDatabaseKey).thenAnswer(
        (_) async => original.asUnmodifiableView(),
      );
      final container = ProviderContainer(
        overrides: [
          securityApiProvider.overrideWithValue(api),
          databaseFileProvider.overrideWith(
            (ref) async => File('${dir.path}/db/baraka.sqlite'),
          ),
        ],
      );
      addTearDown(container.dispose);

      final db = await container.read(appDatabaseProvider.future);
      expect(db.schemaVersion, greaterThanOrEqualTo(1));
      // Asl maʼlumot oʻzgarmagan, tozalash faqat nusxada.
      expect(original.first, 1);
      expect(Directory('${dir.path}/db').existsSync(), isTrue);
    },
  );
}
