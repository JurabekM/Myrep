/// Matnni qoidalar uchun bir xil ko'rinishga keltirish: kichik harf, apostrof
/// variantlari, o'zbek/rus kirill → lotin transliteratsiyasi.
library;

const Map<String, String> _cyr = {
  'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'ғ': "g'", 'д': 'd', 'е': 'e', 'ё': 'yo',
  'ж': 'j', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'қ': 'q', 'л': 'l', 'м': 'm',
  'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ў': "o'",
  'ф': 'f', 'х': 'x', 'ҳ': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch', 'ъ': "'",
  'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
};

final RegExp _apostrophes = RegExp('[ʻʼ`‘’´]');
final RegExp _spaces = RegExp(r'\s+');

String normalizeText(String input) {
  final lower = input.toLowerCase().replaceAll(_apostrophes, "'");
  final sb = StringBuffer();
  for (final rune in lower.runes) {
    final ch = String.fromCharCode(rune);
    sb.write(_cyr[ch] ?? ch);
  }
  return sb.toString().replaceAll(_spaces, ' ').trim();
}
