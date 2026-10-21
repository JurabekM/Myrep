import 'package:flutter/material.dart';

import '../../app/i18n.dart';
import '../../core/core.dart';

/// Maqsadlar (yadrodagi kanonik tartib).
const mfPurposes = ['HOUSEHOLD', 'DEBT', 'BUILD', 'EDUCATION', 'CEREMONY', 'SAVINGS', 'OTHER'];

/// Ish va uy valyutalari ro'yxati (desktop bilan bir xil).
const mfWorkCurrencies = ['KRW', 'RUB', 'KZT', 'TRY', 'USD', 'EUR', 'GBP', 'UZS'];

/// Maqsad → foiz matni (bo'sh — kiritilmagan). Tekshiruv (yig'indi 100 %) — yadroda.
class SharesDraft {
  SharesDraft(Map<String, String> values)
    : controllers = {for (final p in mfPurposes) p: TextEditingController(text: values[p] ?? '')};

  /// Kelishuv shartlaridan yoki standart («Ro'zg'or» 100 %).
  factory SharesDraft.from(List<MfShareDto>? shares) => SharesDraft(
    shares == null || shares.isEmpty ? const {'HOUSEHOLD': '100'} : {for (final s in shares) s.purpose: s.percent},
  );

  final Map<String, TextEditingController> controllers;

  String text(String purpose) => controllers[purpose]!.text.trim();

  List<MfShareInput> input() => [
    for (final p in mfPurposes)
      if (text(p).isNotEmpty) MfShareInput(purpose: p, percent: text(p)),
  ];

  void dispose() {
    for (final c in controllers.values) {
      c.dispose();
    }
  }
}

/// «Ikki qirg'oq» ulushlari: har maqsad uchun foiz (telefon uchun — ikki ustun).
class PurposeShares extends StatelessWidget {
  const PurposeShares({required this.draft, required this.legend, this.onChanged, super.key});

  final SharesDraft draft;
  final String legend;
  final VoidCallback? onChanged;

  @override
  Widget build(BuildContext context) => Semantics(
    container: true,
    label: legend,
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(legend),
        const SizedBox(height: 8),
        Wrap(
          spacing: 12,
          runSpacing: 8,
          children: [
            for (final p in mfPurposes)
              SizedBox(
                width: 160,
                child: TextField(
                  controller: draft.controllers[p],
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  textAlign: TextAlign.end,
                  onChanged: (_) => onChanged?.call(),
                  style: const TextStyle(fontFeatures: [FontFeature.tabularFigures()]),
                  decoration: InputDecoration(
                    labelText: context.t('mf.purpose.$p'),
                    suffixText: '%',
                  ),
                ),
              ),
          ],
        ),
      ],
    ),
  );
}
