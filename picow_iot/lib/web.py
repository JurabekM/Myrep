# -*- coding: utf-8 -*-
"""Lokal async HTTP server — dark-tema dashboard + JSON API.

Marshrutlar:
  GET  /            -> dashboard (HTML)
  GET  /api/data    -> joriy o'lchovlar + tizim holati
  GET  /api/history -> RAM'dagi grafik tarixi
  GET  /api/logs    -> oxirgi log qatorlari
  POST /api/cmd     -> {"cmd": "reboot"|"clear_buffer"|"resync"}
"""

try:
    import asyncio
except ImportError:
    import uasyncio as asyncio

import json
import gc
import config
import logger

_state = None       # main.py dagi AppState obyekti


def bind(state):
    global _state
    _state = state


PAGE = """<!DOCTYPE html><html lang="uz"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__NAME__</title><style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0d1117;color:#e6edf3;font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif;padding:20px}
.wrap{max-width:900px;margin:0 auto}
header{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:22px}
h1{font-size:20px;font-weight:600;letter-spacing:-.02em}
.sub{color:#7d8590;font-size:13px;margin-top:2px}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}
.ok{background:#3fb950;box-shadow:0 0 8px #3fb95088}.bad{background:#f85149}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px}
.card{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:16px}
.card .lbl{color:#7d8590;font-size:12px;text-transform:uppercase;letter-spacing:.06em}
.card .val{font-size:28px;font-weight:600;margin-top:6px;font-variant-numeric:tabular-nums}
.card .unit{font-size:14px;color:#7d8590;margin-left:3px;font-weight:400}
section{margin-top:24px}
h2{font-size:13px;color:#7d8590;text-transform:uppercase;letter-spacing:.06em;margin-bottom:10px}
table{width:100%;border-collapse:collapse;font-size:13px}
td{padding:7px 0;border-bottom:1px solid #21262d}
td:last-child{text-align:right;color:#7d8590;font-variant-numeric:tabular-nums}
pre{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:12px;
    font:12px/1.6 ui-monospace,Consolas,monospace;color:#8b949e;overflow-x:auto;max-height:240px}
button{background:#21262d;color:#e6edf3;border:1px solid #30363d;border-radius:8px;
       padding:8px 14px;font-size:13px;cursor:pointer;margin-right:8px}
button:hover{background:#30363d;border-color:#8b949e}
button.danger:hover{background:#da3633;border-color:#f85149}
svg{width:100%;height:120px;background:#161b22;border:1px solid #30363d;border-radius:10px}
</style></head><body><div class="wrap">
<header>
  <div><h1>__NAME__</h1><div class="sub" id="meta">yuklanmoqda…</div></div>
  <div class="sub"><span class="dot bad" id="d1"></span><span id="s1">Wi-Fi</span>
  &nbsp;<span class="dot bad" id="d2"></span><span id="s2">MQTT</span></div>
</header>
<div class="grid" id="cards"></div>
<section><h2>Harorat tarixi</h2><svg id="chart" viewBox="0 0 600 120" preserveAspectRatio="none"></svg></section>
<section><h2>Tizim</h2><table id="sys"></table></section>
<section><h2>Jurnal</h2><pre id="log"></pre></section>
<section>
  <button onclick="cmd('resync')">NTP sinxron</button>
  <button onclick="cmd('clear_buffer')">Buferni tozalash</button>
  <button class="danger" onclick="cmd('reboot')">Qayta yuklash</button>
</section>
</div><script>
const U={temperature:['Harorat','\\u00B0C'],humidity:['Namlik','%'],pressure:['Bosim','hPa'],
dew_point:['Shudring','\\u00B0C'],altitude:['Balandlik','m'],core_temp:['Chip','\\u00B0C']};
async function tick(){
 try{
  const d=await (await fetch('/api/data')).json();
  document.getElementById('meta').textContent=d.location+' \\u00B7 '+d.ip+' \\u00B7 '+fmt(d.uptime);
  set('d1','s1',d.wifi,'Wi-Fi '+(d.rssi??'')+(d.rssi?' dBm':''));
  set('d2','s2',d.mqtt,'MQTT');
  let h='';
  for(const k in U){if(d.data[k]==null)continue;
    h+=`<div class="card"><div class="lbl">${U[k][0]}</div>
        <div class="val">${d.data[k]}<span class="unit">${U[k][1]}</span></div></div>`;}
  document.getElementById('cards').innerHTML=h;
  document.getElementById('sys').innerHTML=
    row('Bo\\u2018sh RAM',d.free_mem+' B')+row('Flash bo\\u2018sh',d.free_flash+' B')+
    row('Buferdagi yozuv',d.buffered)+row('Yuborilgan',d.published)+
    row('Wi-Fi uzilish',d.wifi_drops)+row('MQTT uzilish',d.mqtt_drops)+
    row('Oxirgi o\\u2018lchov',d.last_read);
  draw((await (await fetch('/api/history')).json()).temperature||[]);
  document.getElementById('log').textContent=(await (await fetch('/api/logs')).json()).lines.join('\\n');
 }catch(e){}
}
function row(a,b){return `<tr><td>${a}</td><td>${b}</td></tr>`}
function set(di,si,on,txt){document.getElementById(di).className='dot '+(on?'ok':'bad');
 document.getElementById(si).textContent=txt}
function fmt(s){const d=s/86400|0,h=s%86400/3600|0,m=s%3600/60|0;
 const hm=String(h).padStart(2,'0')+':'+String(m).padStart(2,'0');
 return (d?d+' kun ':'')+hm;}
function draw(v){const el=document.getElementById('chart');
 if(v.length<2){el.innerHTML='';return}
 const mn=Math.min(...v),mx=Math.max(...v),r=(mx-mn)||1;
 const pts=v.map((y,i)=>[i*600/(v.length-1),110-((y-mn)/r)*95]);
 const line=pts.map(p=>p[0].toFixed(1)+','+p[1].toFixed(1)).join(' ');
 el.innerHTML=`<polyline points="${line}" fill="none" stroke="#58a6ff" stroke-width="2"/>
  <polygon points="0,120 ${line} 600,120" fill="#58a6ff" opacity=".12"/>`;
}
async function cmd(c){if(c==='reboot'&&!confirm('Qurilma qayta yuklansinmi?'))return;
 await fetch('/api/cmd',{method:'POST',body:JSON.stringify({cmd:c})});setTimeout(tick,800)}
tick();setInterval(tick,5000);
</script></body></html>"""


def _response(body, ctype="text/plain", status=200):
    """Har doim bayt qaytaramiz — str yozish oqim implementatsiyasiga bog'liq."""
    if isinstance(body, str):
        body = body.encode()
    head = ("HTTP/1.0 %d OK\r\nContent-Type: %s\r\nContent-Length: %d\r\n"
            "Cache-Control: no-store\r\nConnection: close\r\n\r\n"
            % (status, ctype, len(body)))
    return head.encode() + body


def _json_response(obj, status=200):
    return _response(json.dumps(obj), "application/json", status)


async def _handle(reader, writer):
    try:
        line = await asyncio.wait_for(reader.readline(), 5)
        if not line:
            return
        parts = line.decode().split()
        if len(parts) < 2:
            return
        method, path = parts[0], parts[1]

        # sarlavhalarni o'qib tashlaymiz, Content-Length ni eslab qolamiz
        clen = 0
        while True:
            h = await asyncio.wait_for(reader.readline(), 5)
            if not h or h in (b"\r\n", b"\n"):
                break
            hl = h.decode().lower()
            if hl.startswith("content-length:"):
                clen = int(hl.split(":", 1)[1].strip())

        body = b""
        if clen:
            body = await reader.readexactly(clen) if hasattr(reader, "readexactly") \
                else await reader.read(clen)

        st = _state
        if path == "/" or path.startswith("/index"):
            page = PAGE.replace("__NAME__", config.DEVICE_NAME)
            writer.write(_response(page, "text/html; charset=utf-8"))

        elif path == "/api/data":
            gc.collect()
            writer.write(_json_response({
                "device": config.DEVICE_NAME,
                "location": config.LOCATION,
                "ip": st.ip or "-",
                "wifi": bool(st.wifi_ok),
                "mqtt": bool(st.mqtt_ok),
                "rssi": st.rssi,
                "uptime": st.uptime(),
                "free_mem": gc.mem_free(),
                "free_flash": st.free_flash(),
                "buffered": st.buffered,
                "published": st.published,
                "wifi_drops": st.wifi_drops,
                "mqtt_drops": st.mqtt_drops,
                "last_read": st.last_read_str(),
                "data": st.data or {},
            }))

        elif path == "/api/history":
            writer.write(_json_response(st.history))

        elif path == "/api/logs":
            writer.write(_json_response({"lines": logger.tail(25)}))

        elif path == "/api/cmd" and method == "POST":
            try:
                cmd = json.loads(body).get("cmd", "")
            except ValueError:
                cmd = ""
            ok = st.queue_command(cmd)
            writer.write(_json_response({"ok": ok, "cmd": cmd}))

        else:
            writer.write(b"HTTP/1.0 404 Not Found\r\nContent-Length: 3\r\n"
                         b"Connection: close\r\n\r\n404")

        await writer.drain()
    except Exception as e:
        # Javobsiz uzilish o'rniga 500 — brauzer osilib qolmasin
        logger.warn("web handler xatosi: %r" % e)
        try:
            writer.write(_response("Internal Error", status=500))
            await writer.drain()
        except Exception:
            pass
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def start():
    if not config.WEB_ENABLED:
        return None
    srv = await asyncio.start_server(_handle, "0.0.0.0", config.WEB_PORT)
    logger.info("Web dashboard: http://%s:%d/" % (_state.ip or "0.0.0.0", config.WEB_PORT))
    return srv
