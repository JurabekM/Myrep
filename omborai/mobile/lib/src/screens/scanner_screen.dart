import 'dart:async';
import 'dart:io' show Platform;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:permission_handler/permission_handler.dart';

/// Native Android skaner (Kotlin: CameraX + ML Kit). Topilgan shtrix-kod shu ekranni yopib qaytariladi.
class ScannerScreen extends StatefulWidget {
  const ScannerScreen({super.key});

  static const viewType = 'uz.omborai/scanner';

  @override
  State<ScannerScreen> createState() => _ScannerScreenState();
}

class _ScannerScreenState extends State<ScannerScreen> {
  StreamSubscription<dynamic>? _subscription;
  final _manual = TextEditingController();
  bool _cameraAllowed = false;
  bool _done = false;

  @override
  void initState() {
    super.initState();
    _requestCamera();
  }

  Future<void> _requestCamera() async {
    final status = await Permission.camera.request();
    if (mounted) setState(() => _cameraAllowed = status.isGranted);
  }

  void _onCode(String code) {
    if (_done || !mounted) return;
    _done = true;
    Navigator.of(context).pop(code.trim());
  }

  void _subscribe(int viewId) {
    _subscription?.cancel();
    _subscription = EventChannel('uz.omborai/scanner/events/$viewId')
        .receiveBroadcastStream()
        .listen((event) => _onCode(event as String));
  }

  @override
  void dispose() {
    _subscription?.cancel();
    _manual.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final androidCamera = Platform.isAndroid && _cameraAllowed;
    return Scaffold(
      appBar: AppBar(title: const Text('Shtrix-kod skaneri')),
      body: Column(
        children: [
          Expanded(
            child: androidCamera
                ? AndroidView(
                    viewType: ScannerScreen.viewType,
                    creationParamsCodec: const StandardMessageCodec(),
                    onPlatformViewCreated: _subscribe,
                  )
                : Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Text(
                        Platform.isAndroid
                            ? "Kameraga ruxsat berilmagan. Sozlamalardan ruxsat bering yoki kodni qo'lda kiriting."
                            : "Kamera skaneri faqat Android qurilmada ishlaydi. Kodni qo'lda kiriting.",
                        textAlign: TextAlign.center,
                      ),
                    ),
                  ),
          ),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _manual,
                    keyboardType: TextInputType.number,
                    onSubmitted: _onCode,
                    decoration: const InputDecoration(
                      labelText: 'Shtrix-kod',
                      border: OutlineInputBorder(),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                FilledButton(
                  onPressed: () => _onCode(_manual.text),
                  child: const Text('OK'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
