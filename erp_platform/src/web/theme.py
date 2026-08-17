# -*- coding: utf-8 -*-
"""
Professional dark theme — butun web-interfeys uchun yagona CSS.

JavaScript YO'Q: barcha interaktivlik HTML (details/summary, formalar)
va CSS orqali. CSS ``/static/style.css`` manzilida beriladi.
"""

CSS = """
/* ==================== UzERP Dark Theme ==================== */
:root {
  --bg: #0e1117;
  --panel: #161b26;
  --panel-2: #1c2333;
  --border: #283044;
  --text: #e4e9f2;
  --muted: #8d99ae;
  --accent: #4f8cff;
  --accent-h: #6ba0ff;
  --green: #34d399;
  --red: #f87171;
  --amber: #fbbf24;
  --violet: #a78bfa;
  --cyan: #22d3ee;
  --radius: 10px;
  --sidebar-w: 232px;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
html { font-size: 15px; }
body {
  background: var(--bg); color: var(--text);
  font-family: "Segoe UI", "Inter", system-ui, sans-serif;
  min-height: 100vh;
}
a { color: var(--accent); text-decoration: none; }
a:hover { color: var(--accent-h); }

/* ---------- Layout ---------- */
.app { display: flex; min-height: 100vh; }
.sidebar {
  width: var(--sidebar-w); background: var(--panel);
  border-right: 1px solid var(--border);
  position: fixed; top: 0; bottom: 0; left: 0; overflow-y: auto;
  padding-bottom: 24px;
}
.main { flex: 1; margin-left: var(--sidebar-w); display: flex;
        flex-direction: column; min-width: 0; }
.content { padding: 22px 26px; flex: 1; }
@media (max-width: 900px) {
  .sidebar { position: static; width: 100%; height: auto; }
  .app { flex-direction: column; }
  .main { margin-left: 0; }
}

/* ---------- Sidebar ---------- */
.brand {
  display: flex; align-items: center; gap: 10px;
  padding: 18px 16px 14px; border-bottom: 1px solid var(--border);
}
.brand .logo {
  width: 34px; height: 34px; border-radius: 9px; display: grid;
  place-items: center; font-weight: 800; color: #fff; font-size: 15px;
  background: linear-gradient(135deg, #4f8cff, #a78bfa);
}
.brand .name { font-weight: 700; font-size: 1.05rem; letter-spacing: .3px; }
.brand .ver { color: var(--muted); font-size: .7rem; }
.nav-group { margin-top: 10px; }
.nav-group > .nav-title {
  padding: 8px 16px 4px; font-size: .68rem; letter-spacing: .12em;
  text-transform: uppercase; color: var(--muted);
}
.nav-item {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 16px; color: var(--text); font-size: .92rem;
  border-left: 3px solid transparent;
}
.nav-item:hover { background: var(--panel-2); color: var(--text); }
.nav-item.active {
  background: var(--panel-2); border-left-color: var(--accent);
  color: var(--accent-h); font-weight: 600;
}
.nav-item .ico { width: 20px; text-align: center; opacity: .9; }

/* ---------- Topbar ---------- */
.topbar {
  display: flex; align-items: center; gap: 14px;
  padding: 12px 26px; background: var(--panel);
  border-bottom: 1px solid var(--border);
  position: sticky; top: 0; z-index: 10;
}
.topbar form.search { flex: 1; max-width: 440px; }
.topbar input[type=search] {
  width: 100%; padding: 8px 14px; border-radius: 8px;
  border: 1px solid var(--border); background: var(--bg);
  color: var(--text); font-size: .9rem;
}
.topbar .spacer { flex: 1; }
.userbox { display: flex; align-items: center; gap: 10px; }
.userbox .avatar {
  width: 32px; height: 32px; border-radius: 50%;
  background: var(--panel-2); display: grid; place-items: center;
  font-weight: 700; color: var(--accent); border: 1px solid var(--border);
}
.userbox .uname { font-size: .88rem; font-weight: 600; }
.userbox .urole { font-size: .72rem; color: var(--muted); }

/* ---------- Cards / Grid ---------- */
.grid { display: grid; gap: 16px; }
.grid.cols-2 { grid-template-columns: repeat(2, 1fr); }
.grid.cols-3 { grid-template-columns: repeat(3, 1fr); }
.grid.cols-4 { grid-template-columns: repeat(4, 1fr); }
@media (max-width: 1200px) { .grid.cols-4 { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 1100px) { .grid.cols-3 { grid-template-columns: 1fr; }
                             .grid.cols-2 { grid-template-columns: 1fr; } }
.card {
  background: var(--panel); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 18px;
}
.card > h3 {
  font-size: .95rem; margin-bottom: 12px; color: var(--text);
  display: flex; justify-content: space-between; align-items: center;
}
.stat { display: flex; flex-direction: column; gap: 4px; }
.stat .label { color: var(--muted); font-size: .78rem; }
.stat .value { font-size: 1.45rem; font-weight: 700; letter-spacing: .3px; }
.stat .sub { font-size: .75rem; color: var(--muted); }
.stat.green .value { color: var(--green); }
.stat.red .value { color: var(--red); }
.stat.amber .value { color: var(--amber); }
.stat.accent .value { color: var(--accent-h); }

/* ---------- Page header ---------- */
.page-head {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 18px; gap: 12px; flex-wrap: wrap;
}
.page-head h1 { font-size: 1.35rem; font-weight: 700; }
.page-head .actions { display: flex; gap: 8px; flex-wrap: wrap; }

/* ---------- Buttons ---------- */
.btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 8px 14px; border-radius: 8px; border: 1px solid var(--border);
  background: var(--panel-2); color: var(--text); font-size: .87rem;
  cursor: pointer; font-family: inherit;
}
.btn:hover { border-color: var(--accent); color: var(--accent-h); }
.btn.primary { background: var(--accent); border-color: var(--accent); color: #fff; }
.btn.primary:hover { background: var(--accent-h); color: #fff; }
.btn.danger { background: transparent; border-color: var(--red); color: var(--red); }
.btn.danger:hover { background: rgba(248,113,113,.12); }
.btn.success { background: var(--green); border-color: var(--green); color: #06281c; }
.btn.small { padding: 4px 10px; font-size: .78rem; }
form.inline { display: inline; }

/* ---------- Tables ---------- */
.table-wrap { overflow-x: auto; }
table.data {
  width: 100%; border-collapse: collapse; font-size: .88rem;
}
table.data th {
  text-align: left; padding: 9px 12px; color: var(--muted);
  font-size: .72rem; text-transform: uppercase; letter-spacing: .08em;
  border-bottom: 1px solid var(--border); white-space: nowrap;
}
table.data td {
  padding: 9px 12px; border-bottom: 1px solid rgba(40,48,68,.55);
  vertical-align: middle;
}
table.data tr:hover td { background: rgba(79,140,255,.05); }
table.data td.num, table.data th.num { text-align: right;
  font-variant-numeric: tabular-nums; white-space: nowrap; }
table.data .muted { color: var(--muted); font-size: .8rem; }

/* ---------- Badges ---------- */
.badge {
  display: inline-block; padding: 3px 9px; border-radius: 20px;
  font-size: .72rem; font-weight: 600; letter-spacing: .02em;
}
.badge.gray { background: rgba(141,153,174,.15); color: var(--muted); }
.badge.green { background: rgba(52,211,153,.14); color: var(--green); }
.badge.red { background: rgba(248,113,113,.14); color: var(--red); }
.badge.amber { background: rgba(251,191,36,.14); color: var(--amber); }
.badge.blue { background: rgba(79,140,255,.15); color: var(--accent-h); }
.badge.violet { background: rgba(167,139,250,.15); color: var(--violet); }

/* ---------- Forms ---------- */
.form-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px; }
.form-grid .full { grid-column: 1 / -1; }
@media (max-width: 800px) { .form-grid { grid-template-columns: 1fr; } }
.field label {
  display: block; font-size: .78rem; color: var(--muted); margin-bottom: 5px;
}
.field input, .field select, .field textarea {
  width: 100%; padding: 9px 12px; border-radius: 8px;
  border: 1px solid var(--border); background: var(--bg);
  color: var(--text); font-size: .9rem; font-family: inherit;
}
.field input:focus, .field select:focus, .field textarea:focus {
  outline: none; border-color: var(--accent);
}
.form-actions { margin-top: 16px; display: flex; gap: 10px; }

/* ---------- Alerts ---------- */
.alert { padding: 11px 16px; border-radius: 8px; margin-bottom: 16px;
         font-size: .88rem; border: 1px solid; }
.alert.ok { background: rgba(52,211,153,.1); border-color: rgba(52,211,153,.4);
            color: var(--green); }
.alert.err { background: rgba(248,113,113,.1); border-color: rgba(248,113,113,.4);
             color: var(--red); }

/* ---------- Pagination / Tabs ---------- */
.pagination { display: flex; gap: 6px; margin-top: 14px; align-items: center; }
.pagination a, .pagination span {
  padding: 5px 11px; border-radius: 7px; border: 1px solid var(--border);
  font-size: .82rem; color: var(--text);
}
.pagination .cur { background: var(--accent); border-color: var(--accent);
                   color: #fff; }
.pagination .info { border: none; color: var(--muted); }
.tabs { display: flex; gap: 4px; border-bottom: 1px solid var(--border);
        margin-bottom: 16px; flex-wrap: wrap; }
.tabs a { padding: 8px 16px; font-size: .88rem; color: var(--muted);
          border-bottom: 2px solid transparent; }
.tabs a.active { color: var(--accent-h); border-bottom-color: var(--accent);
                 font-weight: 600; }

/* ---------- Login ---------- */
.login-wrap {
  min-height: 100vh; display: grid; place-items: center;
  background: radial-gradient(1000px 500px at 20% 0%, #16203a 0%, var(--bg) 55%);
}
.login-card {
  width: 380px; max-width: 92vw; background: var(--panel);
  border: 1px solid var(--border); border-radius: 14px; padding: 32px;
}
.login-card .logo-row { display: flex; align-items: center; gap: 12px;
                        margin-bottom: 22px; }
.login-card h1 { font-size: 1.2rem; }
.login-card .sub { color: var(--muted); font-size: .8rem; }
.login-card .field { margin-bottom: 14px; }

/* ---------- SVG charts ---------- */
.chart-box svg { width: 100%; height: auto; display: block; }
.legend { display: flex; gap: 14px; flex-wrap: wrap; margin-top: 10px;
          font-size: .78rem; color: var(--muted); }
.legend .dot { display: inline-block; width: 10px; height: 10px;
               border-radius: 3px; margin-right: 5px; vertical-align: -1px; }

/* ---------- POS ---------- */
.pos-grid { display: grid; grid-template-columns: 1.2fr .8fr; gap: 16px; }
@media (max-width: 1000px) { .pos-grid { grid-template-columns: 1fr; } }
.pos-total { font-size: 1.9rem; font-weight: 800; color: var(--green);
             text-align: right; font-variant-numeric: tabular-nums; }

/* ---------- Misc ---------- */
.muted { color: var(--muted); }
.mt { margin-top: 16px; }
.kv { display: grid; grid-template-columns: 180px 1fr; gap: 6px 14px;
      font-size: .9rem; }
.kv dt { color: var(--muted); }
.kv dd { font-weight: 500; }
hr.sep { border: none; border-top: 1px solid var(--border); margin: 14px 0; }
.footer { padding: 10px 26px; color: var(--muted); font-size: .74rem;
          border-top: 1px solid var(--border); }
@media print {
  .sidebar, .topbar, .page-head .actions, .footer, .pagination { display: none !important; }
  .main { margin: 0; } body { background: #fff; color: #000; }
  .card { border: 1px solid #ccc; background: #fff; }
}
"""
