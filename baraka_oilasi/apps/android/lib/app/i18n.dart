import 'dart:convert';

import 'package:flutter/services.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Ilova tillari (desktop bilan bir xil): `uz` (lotin), `uz-Cyrl`, `ru`.
const locales = ['uz', 'uz-Cyrl', 'ru'];

/// Matnlar `shared/i18n` dan `cargo xtask i18n` orqali ARB sifatida generatsiya qilinadi.
/// Kalitlar desktop bilan bir xil (`home.paidToSelf`), shuning uchun dinamik kalitlar
/// (`error.<CODE>`, `offer.flag.<CODE>`) ham ishlaydi; plaseholderlar — `{name}`.
class Tr {
  Tr(this.locale, this._strings, [this._fallback = const {}]);

  final String locale;
  final Map<String, String> _strings;
  final Map<String, String> _fallback;

  static String _arbKey(String key) => key.replaceAll(RegExp('[.-]'), '_');

  static Map<String, String> parseArb(String json) {
    final raw = jsonDecode(json) as Map<String, dynamic>;
    return {
      for (final e in raw.entries)
        if (!e.key.startsWith('@') && e.value is String) e.key: e.value as String,
    };
  }

  static Future<Tr> load(String locale) async {
    Future<Map<String, String>> read(String tag) async =>
        parseArb(await rootBundle.loadString('lib/l10n/app_${tag.replaceAll('-', '_')}.arb'));
    final strings = await read(locale);
    return Tr(locale, strings, locale == 'uz' ? const {} : await read('uz'));
  }

  bool has(String key) => _strings.containsKey(_arbKey(key)) || _fallback.containsKey(_arbKey(key));

  String call(String key, [Map<String, Object?> params = const {}]) {
    final k = _arbKey(key);
    var s = _strings[k] ?? _fallback[k] ?? key;
    for (final p in params.entries) {
      s = s.replaceAll('{${p.key}}', '${p.value ?? ''}');
    }
    return s;
  }

  /// Flutter `Locale`: `uz-Cyrl` — `uz` skripti bilan.
  Locale get flutterLocale => switch (locale) {
    'uz-Cyrl' => const Locale.fromSubtags(languageCode: 'uz', scriptCode: 'Cyrl'),
    'ru' => const Locale('ru'),
    _ => const Locale('uz'),
  };
}

/// Joriy til: avval shu qurilmada saqlangani (qulf ekrani), ochilgandan keyin — bazadagi sozlama.
final localeProvider = StateProvider<String>((ref) => 'uz');

final trProvider = FutureProvider<Tr>((ref) => Tr.load(ref.watch(localeProvider)));

/// Yuklangan matnlar daraxt bo'ylab (`context.t('app.name')`).
class TrScope extends InheritedWidget {
  const TrScope({required this.tr, required super.child, super.key});

  final Tr tr;

  static Tr of(BuildContext context) {
    final scope = context.dependOnInheritedWidgetOfExactType<TrScope>();
    assert(scope != null, 'TrScope topilmadi');
    return scope!.tr;
  }

  @override
  bool updateShouldNotify(TrScope oldWidget) => oldWidget.tr != tr;
}

extension TrContext on BuildContext {
  Tr get tr => TrScope.of(this);

  String t(String key, [Map<String, Object?> params = const {}]) => TrScope.of(this)(key, params);
}
