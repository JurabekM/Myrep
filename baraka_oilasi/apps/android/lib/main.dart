import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path_provider/path_provider.dart';

import 'app/app.dart';
import 'app/demo.dart';
import 'app/i18n.dart';
import 'bindings/frb_generated.dart';
import 'core/core.dart';
import 'core/platform.dart';
import 'core/prefs.dart';
import 'shared/files.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await RustLib.init();
  // Ilovaning private storage'i (`Context.filesDir`): baza, `keys.bin` va ko'rinish sozlamalari.
  final dir = (await getApplicationSupportDirectory()).path;
  final services = CoreServices(
    core: await BarakaCore.newInstance(dataDir: dir),
    secrets: AndroidSecretSource(),
    window: AndroidSecureWindow(),
    prefs: PrefsStore(dir),
  );
  runApp(
    ProviderScope(
      overrides: [
        servicesProvider.overrideWithValue(services),
        localeProvider.overrideWith((ref) => services.prefs.read().locale ?? 'uz'),
        if (kDemo) shareFileProvider.overrideWithValue(demoShareDisabled),
      ],
      child: const BarakaApp(),
    ),
  );
}
