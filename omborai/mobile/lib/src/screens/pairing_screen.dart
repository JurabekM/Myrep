import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../app_session.dart';

/// Do'kon kalitini ko'rsatish (boshqa qurilmaga juftlash) va boshqa qurilmadan kalit kiritish.
class PairingScreen extends StatefulWidget {
  const PairingScreen({super.key, required this.session});

  final AppSession session;

  @override
  State<PairingScreen> createState() => _PairingScreenState();
}

class _PairingScreenState extends State<PairingScreen> {
  final _input = TextEditingController();
  String? _key;
  String? _message;

  @override
  void initState() {
    super.initState();
    _loadKey();
  }

  @override
  void dispose() {
    _input.dispose();
    super.dispose();
  }

  Future<void> _loadKey() async {
    final bytes = await widget.session.keys.read();
    if (!mounted) return;
    setState(() {
      _key = bytes?.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
    });
  }

  Future<void> _import() async {
    try {
      await widget.session.keys.importHex(_input.text);
      await widget.session.reconnect();
      setState(() => _message = 'Kalit saqlandi, MQTT qayta ulandi');
      await _loadKey();
    } on ArgumentError catch (e) {
      setState(() => _message = '${e.message}');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Juftlash')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text(
            "Bu do'kon kaliti. Boshqa qurilmada kiritib, ma'lumot almashinishni boshlang. "
            "Kalitni hech kimga bermang.",
          ),
          const SizedBox(height: 12),
          SelectableText(
            _key ?? '—',
            style: const TextStyle(fontFamily: 'monospace'),
          ),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: _key == null
                ? null
                : () async {
                    await Clipboard.setData(ClipboardData(text: _key!));
                    if (mounted) setState(() => _message = 'Nusxalandi');
                  },
            icon: const Icon(Icons.copy),
            label: const Text('Nusxalash'),
          ),
          const Divider(height: 32),
          TextField(
            controller: _input,
            decoration: const InputDecoration(
              labelText: 'Boshqa qurilmadan kalit (64 hex belgi)',
            ),
          ),
          const SizedBox(height: 8),
          FilledButton(
            onPressed: _import,
            child: const Text('Kalitni saqlash'),
          ),
          if (_message != null) ...[
            const SizedBox(height: 12),
            Text(_message!),
          ],
        ],
      ),
    );
  }
}
