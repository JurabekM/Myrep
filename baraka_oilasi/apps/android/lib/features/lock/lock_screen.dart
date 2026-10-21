import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../shared/widgets.dart';

/// Qulf ekrani: summalar ko'rinmaydi. PIN yoki tiklash kodi bilan ochiladi.
class LockScreen extends ConsumerStatefulWidget {
  const LockScreen({this.lockedUntil, super.key});

  /// Ko'p xato kiritilgan: shu vaqtgacha kutish (yadro hisoblaydi).
  final String? lockedUntil;

  @override
  ConsumerState<LockScreen> createState() => _LockScreenState();
}

class _LockScreenState extends ConsumerState<LockScreen> with ActionState {
  final _pin = TextEditingController();
  final _code = TextEditingController();
  final _newPin = TextEditingController();
  bool _recovery = false;

  @override
  void dispose() {
    _pin.dispose();
    _code.dispose();
    _newPin.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final actions = ref.read(sessionActionsProvider);
    if (_recovery) {
      await act(() => actions.unlockWithRecovery(_code.text, _newPin.text));
    } else {
      await act(() => actions.unlock(_pin.text));
      _pin.clear();
    }
  }

  String _time(String iso) {
    final d = DateTime.tryParse(iso)?.toLocal();
    if (d == null) return iso;
    String two(int n) => n.toString().padLeft(2, '0');
    return '${two(d.hour)}:${two(d.minute)}:${two(d.second)}';
  }

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Semantics(
                    header: true,
                    child: Text(
                      context.t('lock.title'),
                      style: const TextStyle(fontSize: 26, fontWeight: FontWeight.w700),
                    ),
                  ),
                  const SizedBox(height: 16),
                  if (widget.lockedUntil != null)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: Text(
                        context.t('lock.lockedUntil', {'time': _time(widget.lockedUntil!)}),
                        style: TextStyle(color: p.warn),
                      ),
                    ),
                  if (_recovery) ...[
                    Field(label: context.t('lock.recoveryCode'), controller: _code),
                    const SizedBox(height: 12),
                    PinField(label: context.t('lock.newPin'), controller: _newPin),
                  ] else
                    PinField(
                      label: context.t('lock.pin'),
                      controller: _pin,
                      autofocus: true,
                      onChanged: (v) {
                        if (v.length == 6 && !busy) unawaited(_submit());
                      },
                    ),
                  ErrorText(error),
                  const SizedBox(height: 12),
                  FilledButton(onPressed: busy ? null : _submit, child: Text(context.t('lock.unlock'))),
                  const SizedBox(height: 8),
                  TextButton(
                    onPressed: () => setState(() {
                      _recovery = !_recovery;
                      error = null;
                    }),
                    child: Text(_recovery ? context.t('common.cancel') : context.t('lock.forgot')),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
