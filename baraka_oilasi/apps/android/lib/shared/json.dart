import 'dart:convert';

/// JSON orqali keladigan DTO (sheriklik shartnomasi — `Answer<T>` generik bo'lgani uchun FRB uni
/// Dart klassiga aylantira olmaydi; ADR-0002, Android). Faqat o'qish yordamchilari — hisob yo'q.
typedef Js = Map<String, dynamic>;

Js decodeJs(String json) => jsonDecode(json) as Js;

extension JsRead on Js {
  String s(String k) => (this[k] as String?) ?? '';
  String? so(String k) => this[k] as String?;
  int i(String k) => (this[k] as num?)?.toInt() ?? 0;
  int? io(String k) => (this[k] as num?)?.toInt();
  bool b(String k) => (this[k] as bool?) ?? false;
  Js m(String k) => (this[k] as Js?) ?? const {};
  Js? mo(String k) => this[k] as Js?;
  List<Js> l(String k) => [for (final x in (this[k] as List?) ?? const []) x as Js];
  List<String> ls(String k) => [for (final x in (this[k] as List?) ?? const []) x as String];
  List<int> li(String k) => [for (final x in (this[k] as List?) ?? const []) (x as num).toInt()];

  /// `MoneyDto` → ko'rsatish matni.
  String money(String k) => m(k).s('formatted');

  /// `MoneyDto` → kirish maydoniga qaytariladigan ko'rinish.
  String plain(String k) => m(k).s('plain');
}
