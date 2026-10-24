import 'package:flutter/material.dart';

/// «Baraka Dastur» nishoni: yashil fonda «B» va bug'doy boshog'i
/// (`tools/make_icon.py` yaratadi). Yonida ilova nomi matni bo'lgani uchun
/// ekran o'quvchisiga alohida o'qilmaydi.
class BrandLogo extends StatelessWidget {
  const BrandLogo({this.size = 72, super.key});

  static const asset = 'assets/branding/logo.png';

  final double size;

  @override
  Widget build(BuildContext context) => Image.asset(
    asset,
    key: const Key('brand-logo'),
    width: size,
    height: size,
    excludeFromSemantics: true,
  );
}
