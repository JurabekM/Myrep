#!/usr/bin/env python3
"""
GCOM Signal Logger - Graphical User Interface (GUI Control Panel)
"""

import os
import sys
import time
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path

# Import core logging logic from logger
import logger

class GCOMApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("GCOM Signal Logger - Control Panel")
        self.geometry("780 x 650")
        self.minsize(700, 550)

        # Style configuration
        self.style = ttk.Style(self)
        self.style.theme_use("clam")

        # Color palette
        self.bg_color = "#1e1e2e"
        self.fg_color = "#cdd6f4"
        self.card_bg = "#313244"
        self.accent_color = "#89b4fa"
        self.green_color = "#a6e3a1"
        self.red_color = "#f38ba8"

        self.configure(bg=self.bg_color)
        self._setup_styles()

        self.is_logging = False
        self.logger_thread = None
        self.stop_event = threading.Event()

        # Load config
        self.config_path = logger.DEFAULT_CONFIG
        self.cfg = logger.load_config(self.config_path)

        self._create_widgets()
        self._populate_config_fields()

    def _setup_styles(self):
        self.style.configure(".", background=self.bg_color, foreground=self.fg_color, font=("Segoe UI", 10))
        self.style.configure("TFrame", background=self.bg_color)
        self.style.configure("TLabelframe", background=self.bg_color, foreground=self.accent_color, font=("Segoe UI", 10, "bold"))
        self.style.configure("TLabelframe.Label", background=self.bg_color, foreground=self.accent_color)
        self.style.configure("TLabel", background=self.bg_color, foreground=self.fg_color)
        self.style.configure("Card.TFrame", background=self.card_bg, relief="flat", borderwidth=1)
        self.style.configure("CardHeader.TLabel", background=self.card_bg, foreground="#89dceb", font=("Segoe UI", 9, "bold"))
        self.style.configure("CardVal.TLabel", background=self.card_bg, foreground="#f9e2af", font=("Segoe UI", 14, "bold"))
        self.style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"), foreground=self.accent_color)

        self.style.configure("Start.TButton", font=("Segoe UI", 10, "bold"), foreground="#11111b", background=self.green_color)
        self.style.map("Start.TButton", background=[("active", "#94e2d5")])

        self.style.configure("Stop.TButton", font=("Segoe UI", 10, "bold"), foreground="#11111b", background=self.red_color)
        self.style.map("Stop.TButton", background=[("active", "#eba0ac")])

        self.style.configure("Action.TButton", font=("Segoe UI", 9), foreground="#11111b", background=self.accent_color)
        self.style.map("Action.TButton", background=[("active", "#b4befe")])

    def _create_widgets(self):
        # Header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", px=15, py=10)

        title_lbl = ttk.Label(header_frame, text="GCOM 4G/5G Signal Logger", style="Title.TLabel")
        title_lbl.pack(side="left")

        self.status_lbl = ttk.Label(header_frame, text="● To'xtatilgan", font=("Segoe UI", 11, "bold"), foreground=self.red_color)
        self.status_lbl.pack(side="right")

        # Configuration Frame
        cfg_frame = ttk.LabelFrame(self, text=" Configuration (config.ini) ")
        cfg_frame.pack(fill="x", px=15, py=5)

        # Config fields grid
        ttk.Label(cfg_frame, text="Router URL:").grid(row=0, column=0, sticky="w", px=8, py=4)
        self.url_ent = ttk.Entry(cfg_frame, width=28)
        self.url_ent.grid(row=0, column=1, px=8, py=4)

        ttk.Label(cfg_frame, text="Login:").grid(row=0, column=2, sticky="w", px=8, py=4)
        self.user_ent = ttk.Entry(cfg_frame, width=15)
        self.user_ent.grid(row=0, column=3, px=8, py=4)

        ttk.Label(cfg_frame, text="Parol:").grid(row=0, column=4, sticky="w", px=8, py=4)
        self.pwd_ent = ttk.Entry(cfg_frame, show="*", width=15)
        self.pwd_ent.grid(row=0, column=5, px=8, py=4)

        ttk.Label(cfg_frame, text="Interfeys:").grid(row=1, column=0, sticky="w", px=8, py=4)
        self.iface_ent = ttk.Entry(cfg_frame, width=28)
        self.iface_ent.grid(row=1, column=1, px=8, py=4)

        ttk.Label(cfg_frame, text="Interval (sek):").grid(row=1, column=2, sticky="w", px=8, py=4)
        self.int_ent = ttk.Entry(cfg_frame, width=15)
        self.int_ent.grid(row=1, column=3, px=8, py=4)

        ttk.Label(cfg_frame, text="Format:").grid(row=1, column=4, sticky="w", px=8, py=4)
        self.fmt_combo = ttk.Combobox(cfg_frame, values=["csv", "jsonl"], width=12, state="readonly")
        self.fmt_combo.grid(row=1, column=5, px=8, py=4)

        ttk.Label(cfg_frame, text="Log fayli:").grid(row=2, column=0, sticky="w", px=8, py=4)
        self.log_ent = ttk.Entry(cfg_frame, width=50)
        self.log_ent.grid(row=2, column=1, columnspan=4, sticky="we", px=8, py=4)

        save_btn = ttk.Button(cfg_frame, text="Saqlash", command=self._save_config)
        save_btn.grid(row=2, column=5, px=8, py=4)

        # Dashboard / Metrics Cards Frame
        cards_frame = ttk.LabelFrame(self, text=" Real-vaqt ko'rsatkichlari ")
        cards_frame.pack(fill="x", px=15, py=5)

        self.cards = {}
        metrics = [
            ("RSSI", "rssi"), ("RSRP", "rsrp"), ("RSRQ", "rsrq"), ("SINR", "sinr"),
            ("BAND", "band"), ("REJIM", "network_type"), ("PCC 1", "pcc_1"), ("SCC SONI", "scc_count")
        ]

        for idx, (title, key) in enumerate(metrics):
            r, c = idx // 4, idx % 4
            card = ttk.Frame(cards_frame, style="Card.TFrame")
            card.grid(row=r, column=c, px=6, py=6, sticky="nsew")
            cards_frame.columnconfigure(c, weight=1)

            t_lbl = ttk.Label(card, text=title, style="CardHeader.TLabel")
            t_lbl.pack(anchor="w", px=8, py=(4, 0))

            v_lbl = ttk.Label(card, text="--", style="CardVal.TLabel")
            v_lbl.pack(anchor="w", px=8, py=(0, 4))

            self.cards[key] = v_lbl

        # Controls & Action buttons frame
        ctrl_frame = ttk.Frame(self)
        ctrl_frame.pack(fill="x", px=15, py=8)

        self.start_btn = ttk.Button(ctrl_frame, text="▶ Kuzatishni boshlash", style="Start.TButton", command=self._toggle_logging)
        self.start_btn.pack(side="left", px=5)

        once_btn = ttk.Button(ctrl_frame, text="⚡ 1 marta tekshirish", style="Action.TButton", command=self._fetch_once)
        once_btn.pack(side="left", px=5)

        open_log_btn = ttk.Button(ctrl_frame, text="📁 Log faylni ochish", style="Action.TButton", command=self._open_log_file)
        open_log_btn.pack(side="left", px=5)

        open_dir_btn = ttk.Button(ctrl_frame, text="📂 Papkani ochish", style="Action.TButton", command=self._open_install_dir)
        open_dir_btn.pack(side="left", px=5)

        # Log Terminal Output
        log_frame = ttk.LabelFrame(self, text=" Tizim jurnali (Console Output) ")
        log_frame.pack(fill="both", expand=True, px=15, py=(5, 15))

        self.log_text = tk.Text(log_frame, bg="#11111b", fg="#a6adc8", insertbackground="#cdd6f4", font=("Consolas", 9.5), relief="flat")
        self.log_text.pack(fill="both", expand=True, px=5, py=5)

    def _populate_config_fields(self):
        self.url_ent.insert(0, self.cfg.get("url", ""))
        self.user_ent.insert(0, self.cfg.get("username", ""))
        self.pwd_ent.insert(0, self.cfg.get("password", ""))
        self.iface_ent.insert(0, self.cfg.get("iface", "4g"))
        self.int_ent.insert(0, str(self.cfg.get("interval", 60)))
        self.fmt_combo.set(self.cfg.get("format", "csv"))
        self.log_ent.insert(0, str(self.cfg.get("logfile", logger.SCRIPT_DIR / "gcom_signal_log.csv")))

    def _save_config(self):
        url = self.url_ent.get().strip()
        user = self.user_ent.get().strip()
        pwd = self.pwd_ent.get().strip()
        iface = self.iface_ent.get().strip()
        try:
            interval = int(self.int_ent.get().strip())
        except ValueError:
            messagebox.showerror("Xato", "Interval butun son bo'lishi kerak!")
            return

        fmt = self.fmt_combo.get()
        logfile = self.log_ent.get().strip()

        # Update INI file
        parser = logger.configparser.ConfigParser()
        parser["gcom"] = {
            "url": url,
            "username": user,
            "password": pwd,
            "iface": iface,
            "interval": str(interval),
            "logfile": logfile,
            "format": fmt
        }
        with open(self.config_path, "w", encoding="utf-8") as f:
            parser.write(f)

        self.cfg = logger.load_config(self.config_path)
        self.log_msg("✓ Sozlamalar config.ini fayliga saqlandi.")

    def log_msg(self, text):
        def _write():
            self.log_text.insert("end", text + "\n")
            self.log_text.see("end")
        self.after(0, _write)

    def update_metrics(self, record):
        def _update():
            for key, widget in self.cards.items():
                val = record.get(key, "--")
                widget.config(text=str(val) if val else "--")
        self.after(0, _update)

    def _toggle_logging(self):
        if not self.is_logging:
            self._start_logging()
        else:
            self._stop_logging()

    def _start_logging(self):
        self._save_config()
        self.is_logging = True
        self.stop_event.clear()
        self.start_btn.config(text="■ Kuzatishni to'xtatish", style="Stop.TButton")
        self.status_lbl.config(text="● Kuzatilmoqda...", foreground=self.green_color)

        self.logger_thread = threading.Thread(target=self._logging_worker, daemon=True)
        self.logger_thread.start()

    def _stop_logging(self):
        self.is_logging = False
        self.stop_event.set()
        self.start_btn.config(text="▶ Kuzatishni boshlash", style="Start.TButton")
        self.status_lbl.config(text="● To'xtatilgan", foreground=self.red_color)
        self.log_msg("[!] Kuzatish to'xtatildi.")

    def _logging_worker(self):
        session = logger.requests.Session()
        self.log_msg(f"[{logger.datetime.now().strftime('%H:%M:%S')}] {self.cfg['url']} ga ulaninmoqda...")

        try:
            if not logger.login(session, self.cfg["url"], self.cfg["username"], self.cfg["password"]):
                self.log_msg("XATO: Routerga login qilib bo'lmadi! Login/parolni tekshiring.")
                self.after(0, self._stop_logging)
                return
        except Exception as e:
            self.log_msg(f"XATO: {e}")
            self.after(0, self._stop_logging)
            return

        self.log_msg("✓ Login muvaffaqiyatli. Monitor boshlandi.")
        interval = self.cfg["interval"]
        logfile = Path(self.cfg["logfile"])

        while not self.stop_event.is_set():
            try:
                record = logger.collect_once(self.cfg, session)
                logger.append_log(logfile, self.cfg["format"], record)
                self.update_metrics(record)

                ts = record.get("timestamp", logger.datetime.now().isoformat())
                summary = (
                    f"[{ts}] RSSI: {record.get('rssi')} | RSRP: {record.get('rsrp')} | "
                    f"RSRQ: {record.get('rsrq')} | SINR: {record.get('sinr')} | Band: {record.get('band')}"
                )
                self.log_msg(summary)
            except Exception as e:
                self.log_msg(f"Xatolik: {e}")

            # Sleep in small increments to respond quickly to stop signal
            for _ in range(interval * 2):
                if self.stop_event.is_set():
                    break
                time.sleep(0.5)

    def _fetch_once(self):
        def _worker():
            self.log_msg("⚡ Bir marta o'qish bajarilmoqda...")
            session = logger.requests.Session()
            try:
                if logger.login(session, self.cfg["url"], self.cfg["username"], self.cfg["password"]):
                    record = logger.collect_once(self.cfg, session)
                    logger.append_log(Path(self.cfg["logfile"]), self.cfg["format"], record)
                    self.update_metrics(record)
                    self.log_msg("✓ Ma'lumot o'qildi va log faylga yozildi.")
                else:
                    self.log_msg("XATO: Login amalga oshmadi.")
            except Exception as e:
                self.log_msg(f"XATO: {e}")
        threading.Thread(target=_worker, daemon=True).start()

    def _open_log_file(self):
        logfile = Path(self.cfg.get("logfile", logger.SCRIPT_DIR / "gcom_signal_log.csv"))
        if logfile.exists():
            os.startfile(str(logfile))
        else:
            messagebox.showinfo("Ma'lumot", f"Log fayl hali mavjud emas: {logfile}")

    def _open_install_dir(self):
        os.startfile(str(logger.SCRIPT_DIR))


if __name__ == "__main__":
    app = GCOMApp()
    app.mainloop()
