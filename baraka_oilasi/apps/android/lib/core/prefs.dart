import 'dart:convert';
import 'dart:io';

/// Shu qurilmaning ko'rinish sozlamalari: til (qulf ekranida ham kerak — baza hali ochilmagan),
/// shrift masshtabi va mavzu. Maxfiy emas — summalar bu yerga tushmaydi (desktop `prefs.ts`).
class DisplayPrefs {
  const DisplayPrefs({this.locale, this.fontScale = 100, this.theme = 'dark'});

  factory DisplayPrefs.fromJson(Map<String, dynamic> j) => DisplayPrefs(
    locale: j['locale'] is String ? j['locale'] as String : null,
    fontScale: fontScales.contains(j['fontScale']) ? j['fontScale'] as int : 100,
    theme: j['theme'] == 'light' ? 'light' : 'dark',
  );

  static const fontScales = [100, 115, 130, 150];

  final String? locale;
  final int fontScale;
  final String theme;

  bool get dark => theme != 'light';

  DisplayPrefs copyWith({String? locale, int? fontScale, String? theme}) => DisplayPrefs(
    locale: locale ?? this.locale,
    fontScale: fontScale ?? this.fontScale,
    theme: theme ?? this.theme,
  );

  Map<String, Object?> toJson() => {'locale': locale, 'fontScale': fontScale, 'theme': theme};
}

class PrefsStore {
  PrefsStore(this.dir);

  final String dir;

  File get _file => File('$dir/display.json');

  DisplayPrefs read() {
    try {
      return DisplayPrefs.fromJson(jsonDecode(_file.readAsStringSync()) as Map<String, dynamic>);
    } on Object {
      return const DisplayPrefs();
    }
  }

  void write(DisplayPrefs p) {
    try {
      _file.writeAsStringSync(jsonEncode(p.toJson()));
    } on Object {
      // saqlanmasa ham joriy sessiyada qo'llanadi
    }
  }
}
