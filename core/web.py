import hmac
import json
import logging
from aiohttp import web
from config import CONFIG_FILE, cfg, DASHBOARD_TOKEN, runtime
from core.storage import get_active_chats_count, get_appointments_count
from core.utils import msg_times

logger = logging.getLogger("mediassistant.web")

## TEMPLATES
DASHBOARD_HTML = """<!DOCTYPE html>
<html>
    <head>
        <title>Clinic Bot</title>
            <meta name="viewport" content="width=device-width,initial-scale=1">
<style>
    body    {font-family:system-ui;background:#111;color:#fff;padding:20px;max-width:600px;margin:0 auto}
    .card   {background:#1a1a1a;padding:20px;border-radius:12px;margin:15px 0}
    h1      {color:#2ed573}h2{font-size:18px;margin-top:0}
    .status {display:inline-block;padding:8px 20px;border-radius:20px;font-weight:bold}
    .on     {background:#2ed573;color:#000}.off{background:#ff4757}
    button  {background:#2ed573;color:#000;border:none;padding:12px 24px;border-radius:8px;margin:5px;cursor:pointer;font-size:14px}
    button:hover{opacity:0.8}input{padding:10px;border-radius:6px;border:1px solid #333;background:#222;color:#fff;width:100%;margin:8px 0}
    .stats  {display:grid;grid-template-columns:1fr 1fr;gap:10px}
    .stat   {background:#222;padding:15px;border-radius:8px;text-align:center}
    .num    {font-size:28px;color:#2ed573;font-weight:bold}
    .err    {color:#ff4757;font-size:13px}
</style>
</head>

<body>
    <h1>Clinic Bot</h1>

    <div class="card" id="loginCard">
        <h2>Dashboard access token</h2>
        <input type="password" id="tokenInput" placeholder="Paste dashboard token">
        <button onclick="saveToken()">Unlock</button>
        <div class="err" id="loginErr"></div>
    </div>

    <div id="app" style="display:none">
        <div class="card">
            <div id="status"></div>
            <button onclick="toggle()">Toggle On/Off</button>
            <button onclick="refresh()">Refresh</button>
            <button onclick="logout()">Lock</button>
        </div>
        <div class="card">
            <h2>Stats</h2>
            <div class="stats" id="stats"></div>
        </div>
        <div class="card">
            <h2>Config</h2>
            <input type="number" id="rate" placeholder="Max msgs/hour">
            <input type="number" id="delay" placeholder="Delay seconds">
            <input type="number" id="temp" placeholder="Temperature (0-1)" step="0.1" min="0" max="1">
            <button onclick="update()">Update</button>
        </div>
    </div>

<script>
const API='/api';
function getToken(){ return sessionStorage.getItem('dashboard_token') || ''; }
function saveToken(){
    const t = document.getElementById('tokenInput').value.trim();
    if(!t) return;
    sessionStorage.setItem('dashboard_token', t);
    document.getElementById('loginErr').textContent = '';
    boot();
}
function logout(){
    sessionStorage.removeItem('dashboard_token');
    document.getElementById('app').style.display='none';
    document.getElementById('loginCard').style.display='block';
}
async function api(u,m,b) {
    let o={method:m,headers:{'Content-Type':'application/json','Authorization':'Bearer '+getToken()}};
    if(b)o.body=JSON.stringify(b);
    let r=await fetch(API+u,o);
    if(r.status===401){
        document.getElementById('app').style.display='none';
        document.getElementById('loginCard').style.display='block';
        document.getElementById('loginErr').textContent = 'Invalid or missing token.';
        throw new Error('unauthorized');
    }
    return r.json()
}
async function toggle() {
    let d=await api('/toggle','POST');
    document.getElementById('status').innerHTML=`<span class="status ${d.enabled?'on':'off'}">${d.enabled?'ACTIVE':'STOPPED'}</span>`
}
async function refresh() {
    let s=await api('/stats');
    document.getElementById('status').innerHTML=`<span class="status ${s.enabled?'on':'off'}">${s.enabled?'ACTIVE':'STOPPED'}</span>`;
    document.getElementById('stats').innerHTML=`<div class="stat"><div class="num">${s.active_chats}</div>chats (1h)</div><div class="stat"><div class="num">${s.appointments_in_progress}</div>booking in progress</div><div class="stat"><div class="num">${s.appointments_confirmed}</div>confirmed total</div><div class="stat"><div class="num">${s.msgs_this_hour}/${s.rate_limit}</div>msgs/hr</div>`;
    let c=await api('/config');
    document.getElementById('rate').value=c.max_messages_per_hour;
    document.getElementById('delay').value=c.delay_seconds;
    document.getElementById('temp').value=c.temperature
}
async function update() {
    await api('/config','POST',{max_messages_per_hour:parseInt(document.getElementById('rate').value),delay_seconds:parseInt(document.getElementById('delay').value),temperature:parseFloat(document.getElementById('temp').value)});
    refresh()
}
function boot(){
    if(!getToken()) return;
    document.getElementById('loginCard').style.display='none';
    document.getElementById('app').style.display='block';
    refresh().catch(()=>{});
}
boot();
</script>
</body>
</html>"""


## AUTH
def _is_authorized(request):
    auth = request.headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else ""
    return hmac.compare_digest(token, DASHBOARD_TOKEN)


@web.middleware
async def auth_middleware(request, handler):
    if request.path.startswith("/api/"):
        if not _is_authorized(request):
            return web.json_response({"error": "unauthorized"}, status=401)
    return await handler(request)


##SERVER
async def api_config(request):
    # Only expose the non-secret, dashboard-tunable subset - 
    
    return web.json_response({
        "enabled": runtime.enabled,
        "reply_to_dms": runtime.reply_dms,
        "reply_to_groups": runtime.reply_groups,
        "delay_seconds": runtime.delay,
        "max_messages_per_hour": runtime.rate_limit,
        "temperature": cfg.get("temperature"),
    })

async def api_toggle(request):
    runtime.enabled = not runtime.enabled
    _persist()
    logger.info("Bot toggled %s via dashboard", "ON" if runtime.enabled else "OFF")
    return web.json_response({"enabled": runtime.enabled})

async def api_stats(request):
    appt_counts = await get_appointments_count()
    return web.json_response({
        "enabled": runtime.enabled,
        "active_chats": await get_active_chats_count(),
        "appointments_in_progress": appt_counts["in_progress"],
        "appointments_confirmed": appt_counts["confirmed"],
        "msgs_this_hour": len(msg_times),
        "rate_limit": runtime.rate_limit
    })

async def api_update_config(request):
    try:
        data = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"error": "invalid JSON body"}, status=400)

    # Validate before applying anything - a bad partial update shouldn't be
    # able to corrupt runtime state or config.json.
    allowed = {
        "enabled", "reply_to_dms", "reply_to_groups",
        "delay_seconds", "max_messages_per_hour",
    }
    unknown = set(data.keys()) - allowed - {"temperature"}
    if unknown:
        return web.json_response({"error": f"unknown field(s): {sorted(unknown)}"}, status=400)

    try:
        if "delay_seconds" in data:
            data["delay_seconds"] = max(0, int(data["delay_seconds"]))
        if "max_messages_per_hour" in data:
            data["max_messages_per_hour"] = max(1, int(data["max_messages_per_hour"]))
        if "temperature" in data:
            temp = float(data["temperature"])
            if not (0.0 <= temp <= 1.0):
                raise ValueError("temperature out of range")
            cfg["temperature"] = temp
    except (TypeError, ValueError) as e:
        return web.json_response({"error": f"invalid value: {e}"}, status=400)

    runtime.apply(data)
    _persist()
    return web.json_response({"status": "ok"})

def _persist():
    """Write current runtime + cfg state back to config.json."""
    merged = runtime.to_cfg_dict(cfg)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(merged, f, indent=2)

async def dashboard(request):
    return web.Response(text=DASHBOARD_HTML, content_type='text/html')

def setup_web_server():
    """Setup and return the web application"""
    app = web.Application(middlewares=[auth_middleware])
    app.router.add_get('/api/config', api_config)
    app.router.add_post('/api/config', api_update_config)
    app.router.add_post('/api/toggle', api_toggle)
    app.router.add_get('/api/stats', api_stats)
    app.router.add_get('/', dashboard)
    return app
