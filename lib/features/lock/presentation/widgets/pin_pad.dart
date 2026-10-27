import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/core/security/pin/pin_policy.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// PIN nuqtalari + raqamli klaviatura. 6-raqam kiritilganda [onCompleted]
/// chaqiriladi va maydon tozalanadi. Tizim klaviaturasi ishlatilmaydi —
/// klaviatura ilovalari kiritilgan raqamlarni ko'rmaydi.
class PinPad extends StatefulWidget {
  const PinPad({
    required this.onCompleted,
    this.enabled = true,
    this.onBiometric,
    super.key,
  });

  final ValueChanged<String> onCompleted;
  final bool enabled;

  /// `null` bo'lsa biometriya tugmasi ko'rsatilmaydi.
  final VoidCallback? onBiometric;

  @override
  State<PinPad> createState() => _PinPadState();
}

class _PinPadState extends State<PinPad> {
  final _digits = StringBuffer();

  void _press(String digit) {
    if (!widget.enabled || _digits.length >= PinPolicy.length) return;
    HapticFeedback.selectionClick();
    setState(() => _digits.write(digit));
    if (_digits.length == PinPolicy.length) {
      final pin = _digits.toString();
      _digits.clear();
      widget.onCompleted(pin);
    }
  }

  void _backspace() {
    if (!widget.enabled || _digits.isEmpty) return;
    final current = _digits.toString();
    setState(() {
      _digits
        ..clear()
        ..write(current.substring(0, current.length - 1));
    });
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final l10n = context.l10n;
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Semantics(
          key: const Key('pin-dots'),
          label: l10n.pinDigitsEntered(_digits.length),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              for (var i = 0; i < PinPolicy.length; i++)
                AnimatedContainer(
                  duration: const Duration(milliseconds: 120),
                  margin: const EdgeInsets.symmetric(horizontal: 8),
                  width: 14,
                  height: 14,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: i < _digits.length
                        ? scheme.primary
                        : Colors.transparent,
                    border: Border.all(color: scheme.primary, width: 1.5),
                  ),
                ),
            ],
          ),
        ),
        const SizedBox(height: 32),
        for (final row in const [
          ['1', '2', '3'],
          ['4', '5', '6'],
          ['7', '8', '9'],
        ])
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [for (final d in row) _DigitKey(d, onTap: _press)],
          ),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            if (widget.onBiometric != null)
              _IconKey(
                key: const Key('pin-biometric'),
                icon: Icons.fingerprint,
                label: l10n.pinKeyBiometric,
                onTap: widget.enabled ? widget.onBiometric : null,
              )
            else
              const SizedBox(width: _keySize + 2 * _keyGap),
            _DigitKey('0', onTap: _press),
            _IconKey(
              key: const Key('pin-backspace'),
              icon: Icons.backspace_outlined,
              label: l10n.pinKeyDelete,
              onTap: widget.enabled ? _backspace : null,
            ),
          ],
        ),
      ],
    );
  }
}

const double _keySize = 72;
const double _keyGap = 10;

class _DigitKey extends StatelessWidget {
  const _DigitKey(this.digit, {required this.onTap});

  final String digit;
  final ValueChanged<String> onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.all(_keyGap),
      child: Material(
        color: theme.colorScheme.surfaceContainerLow,
        shape: CircleBorder(
          side: BorderSide(color: theme.colorScheme.outlineVariant),
        ),
        child: InkWell(
          key: Key('pin-key-$digit'),
          customBorder: const CircleBorder(),
          onTap: () => onTap(digit),
          child: SizedBox.square(
            dimension: _keySize,
            child: Center(
              child: Text(digit, style: theme.textTheme.headlineSmall),
            ),
          ),
        ),
      ),
    );
  }
}

class _IconKey extends StatelessWidget {
  const _IconKey({
    required this.icon,
    required this.label,
    required this.onTap,
    super.key,
  });

  final IconData icon;
  final String label;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(_keyGap),
      child: SizedBox.square(
        dimension: _keySize,
        child: IconButton(
          tooltip: label,
          iconSize: 28,
          icon: Icon(icon),
          onPressed: onTap,
        ),
      ),
    );
  }
}
