# Privacy policy — Sector Verify

**In short: the app collects no data and sends nothing to anyone.**

- **Location (GPS) and cellular measurements** (RSRP, PCI, ARFCN, TA) are collected only during a survey you start and are
  stored **only on your phone**, in an encrypted database (SQLCipher). Background location is not used.
- **SIM data** (MCC/MNC) is read only to pick the SIM that matches the plan; IMSI, phone number and IMEI are not read.
- **Network:** the only request is an empty `HEAD` to the optional HTTPS address you enter in Settings (to keep the phone in
  connected mode). It carries no personal or measurement data.
- **No telemetry, analytics, ads, Firebase or Google Play Services.**
- **Backups:** app data is excluded from cloud backup and device-to-device transfer.
- **Sharing:** PDF reports and session ZIPs leave the phone only when you share them yourself.
- **Crash log:** on a crash only the stack trace is stored on the phone; only you can export it.
- **Deletion:** uninstalling the app or clearing its data deletes everything.
