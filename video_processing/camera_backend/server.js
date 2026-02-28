const express = require("express");
const http    = require("http");
const app     = express();

// ── Proxy to Python :5001 ─────────────────────────────────────────────────────
function proxyJSON(path, res) {
  const req = http.get(`http://127.0.0.1:5001${path}`, (pRes) => {
    let raw = "";
    pRes.on("data", (d) => (raw += d));
    pRes.on("end", () => {
      res.setHeader("Access-Control-Allow-Origin", "*");
      res.setHeader("Cache-Control", "no-cache, no-store");
      res.setHeader("Content-Type", "application/json");
      res.send(raw);
    });
  });
  req.on("error", () => {
    res.status(503).json({
      known: [], unknown: [],
      counts: { known: 0, unknown: 0, total: 0 },
      alerts: [], timestamp: Date.now() / 1000,
      _offline: true
    });
  });
}

app.get("/data",   (req, res) => proxyJSON("/data", res));
app.get("/health", (req, res) => proxyJSON("/health", res));

app.get("/live", (req, res) => {
  http.get("http://127.0.0.1:5001/video_feed", (pRes) => {
    res.writeHead(pRes.statusCode, pRes.headers);
    pRes.pipe(res);
  }).on("error", () => res.status(503).send("Stream offline — is multiple_tracking.py running?"));
});

// ── Dashboard ─────────────────────────────────────────────────────────────────
app.get("/", (req, res) => res.send(`<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NEXUS — Surveillance Intelligence</title>
<link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;600;700&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#040608;--panel:#07090c;--border:#0e2218;
  --green:#00ff88;--gd:#00bb60;
  --red:#ff2244;--rd:#991122;
  --yellow:#ffcc00;--cyan:#00ccff;
  --text:#c0d8c0;--dim:#3a5a4a;
  --glow:0 0 14px rgba(0,255,136,.3);
  --glow-r:0 0 14px rgba(255,34,68,.35);
}
*{box-sizing:border-box;margin:0;padding:0}
body{
  background:var(--bg);color:var(--text);
  font-family:'Rajdhani',sans-serif;height:100vh;overflow:hidden;
  background-image:
    repeating-linear-gradient(0deg,transparent,transparent 39px,rgba(0,255,136,.018) 40px),
    repeating-linear-gradient(90deg,transparent,transparent 39px,rgba(0,255,136,.018) 40px);
}
/* scanlines */
body::after{
  content:'';position:fixed;inset:0;pointer-events:none;z-index:9999;
  background:repeating-linear-gradient(to bottom,transparent 0,transparent 2px,rgba(0,0,0,.06) 2px,rgba(0,0,0,.06) 4px);
}

/* ── HEADER ── */
header{
  display:flex;align-items:center;justify-content:space-between;
  padding:10px 22px;border-bottom:1px solid var(--border);
  background:linear-gradient(180deg,#060d09,var(--bg));
  height:52px;
}
.logo{font-family:'Share Tech Mono',monospace;font-size:1.35rem;color:var(--green);text-shadow:var(--glow);letter-spacing:5px}
.logo small{display:block;font-size:.6rem;letter-spacing:3px;color:var(--dim);margin-top:-2px}
.hright{display:flex;align-items:center;gap:20px}
.sysline{display:flex;align-items:center;gap:7px;font-family:'Share Tech Mono',monospace;font-size:.7rem;color:var(--dim)}
.dot{width:8px;height:8px;border-radius:50%}
.dot-g{background:var(--green);box-shadow:var(--glow);animation:pulse 2s infinite}
.dot-r{background:var(--red);box-shadow:var(--glow-r)}
.dot-y{background:var(--yellow)}
#clock{font-family:'Share Tech Mono',monospace;font-size:.85rem;color:var(--green);letter-spacing:2px}

/* ── LAYOUT ── */
.wrap{display:grid;grid-template-columns:1fr 320px;grid-template-rows:48px 1fr;height:calc(100vh - 52px)}

/* ── STATS BAR ── */
.stats{
  grid-column:1/-1;display:flex;gap:1px;
  background:var(--border);border-bottom:1px solid var(--border);
}
.sc{
  flex:1;background:var(--panel);padding:8px 18px;
  display:flex;align-items:center;gap:10px;transition:background .2s;cursor:default;
}
.sc:hover{background:#080f0b}
.si{font-size:1.2rem}
.sl{font-size:.58rem;letter-spacing:2px;color:var(--dim);text-transform:uppercase}
.sv{font-size:1.5rem;font-weight:700;color:var(--green);line-height:1}
.sv.r{color:var(--red)} .sv.y{color:var(--yellow);font-size:.85rem}

/* ── VIDEO ── */
.vpane{
  position:relative;background:#000;
  border-right:1px solid var(--border);
  display:flex;align-items:center;justify-content:center;overflow:hidden;
}
.vpane img{width:100%;height:100%;object-fit:contain;display:block}
.corner{position:absolute;width:18px;height:18px;border-color:var(--green);border-style:solid;opacity:.6}
.tl{top:8px;left:8px;border-width:2px 0 0 2px}
.tr{top:8px;right:8px;border-width:2px 2px 0 0}
.bl{bottom:8px;left:8px;border-width:0 0 2px 2px}
.br{bottom:8px;right:8px;border-width:0 2px 2px 0}
.livebadge{
  position:absolute;top:14px;left:50%;transform:translateX(-50%);
  background:var(--red);color:#fff;font-family:'Share Tech Mono',monospace;
  font-size:.6rem;letter-spacing:3px;padding:3px 10px;
  animation:blinkbg 1.2s infinite;
}
.vinfo{
  position:absolute;bottom:10px;left:10px;
  font-family:'Share Tech Mono',monospace;font-size:.6rem;
  color:rgba(0,255,136,.55);line-height:1.9;
}
.offline-overlay{
  position:absolute;inset:0;background:rgba(0,0,0,.8);
  display:none;align-items:center;justify-content:center;flex-direction:column;gap:12px;
  font-family:'Share Tech Mono',monospace;color:var(--red);font-size:.9rem;letter-spacing:2px;
}

/* ── SIDE PANEL ── */
.spanel{display:flex;flex-direction:column;background:var(--panel);overflow:hidden}
.psec{border-bottom:1px solid var(--border);display:flex;flex-direction:column;min-height:0}
.psec.grow{flex:1;overflow:hidden}
.phdr{
  padding:8px 14px;font-family:'Share Tech Mono',monospace;
  font-size:.6rem;letter-spacing:3px;color:var(--dim);
  border-bottom:1px solid var(--border);
  display:flex;align-items:center;gap:7px;flex-shrink:0;
}
.pbody{padding:8px;overflow-y:auto;max-height:200px}
.psec.grow .pbody{max-height:none;flex:1}

/* ── CARDS ── */
.card{
  border:1px solid var(--border);border-radius:3px;
  padding:9px 11px;margin-bottom:7px;position:relative;transition:background .15s;
}
.card:last-child{margin-bottom:0}
.card.known{border-left:3px solid var(--green);background:rgba(0,255,136,.025)}
.card.known:hover{background:rgba(0,255,136,.05)}
.card.unk{border-left:3px solid var(--red);background:rgba(255,34,68,.03)}
.card.unk:hover{background:rgba(255,34,68,.06)}
.card.scan{border-left:3px solid var(--yellow);background:rgba(255,204,0,.02)}
.fname{font-size:.95rem;font-weight:700;letter-spacing:2px;margin-bottom:5px}
.fname.g{color:var(--green)} .fname.r{color:var(--red)} .fname.y{color:var(--yellow)}
.cgrid{
  display:grid;grid-template-columns:1fr 1fr;gap:2px 6px;
  font-family:'Share Tech Mono',monospace;font-size:.6rem;
}
.ci{display:flex;justify-content:space-between}
.ck{color:var(--dim)} .cv{color:var(--text)}
.badge{
  position:absolute;top:7px;right:7px;
  font-family:'Share Tech Mono',monospace;font-size:.5rem;letter-spacing:2px;padding:2px 5px;border-radius:2px;
}
.bg{background:rgba(0,255,136,.12);color:var(--green)}
.br2{background:rgba(255,34,68,.12);color:var(--red);animation:blinktext 1s infinite}
.by{background:rgba(255,204,0,.1);color:var(--yellow)}
.empty{
  text-align:center;padding:20px 8px;
  font-family:'Share Tech Mono',monospace;font-size:.62rem;color:var(--dim);letter-spacing:2px;
}

/* ── ALERT LOG ── */
.alist{flex:1;overflow-y:auto;padding:6px}
.aitem{
  display:flex;align-items:center;gap:8px;padding:4px 6px;margin-bottom:2px;
  border-radius:2px;font-family:'Share Tech Mono',monospace;font-size:.6rem;
  animation:fadeIn .25s ease;
}
.aitem.ka{background:rgba(0,255,136,.05);color:var(--gd)}
.aitem.ua{background:rgba(255,34,68,.07);color:var(--red)}
.at{color:var(--dim);flex-shrink:0}
.an{font-weight:bold;letter-spacing:2px}

@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.35;transform:scale(.8)}}
@keyframes blinkbg{0%,100%{opacity:1}50%{opacity:.35}}
@keyframes blinktext{0%,100%{opacity:1}50%{opacity:.25}}
@keyframes fadeIn{from{opacity:0;transform:translateX(6px)}to{opacity:1;transform:none}}
::-webkit-scrollbar{width:3px}
::-webkit-scrollbar-track{background:var(--bg)}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px}
</style>
</head>
<body>
<header>
  <div class="logo">NEXUS<small>SURVEILLANCE INTELLIGENCE v2.1</small></div>
  <div class="hright">
    <div class="sysline"><div class="dot dot-g" id="sdot"></div><span id="stxt">SYSTEM ONLINE</span></div>
    <div id="clock">--:--:--</div>
  </div>
</header>

<div class="wrap">
  <!-- STATS BAR -->
  <div class="stats">
    <div class="sc"><div class="si">👁</div><div><div class="sl">Detected</div><div class="sv" id="sT">0</div></div></div>
    <div class="sc"><div class="si">✅</div><div><div class="sl">Identified</div><div class="sv" id="sK">0</div></div></div>
    <div class="sc"><div class="si">⚠️</div><div><div class="sl">Unknown</div><div class="sv r" id="sU">0</div></div></div>
    <div class="sc"><div class="si">🕐</div><div><div class="sl">Last Update</div><div class="sv y" id="sL">--:--:--</div></div></div>
  </div>

  <!-- VIDEO -->
  <div class="vpane">
    <img src="/live" alt="Live Feed" id="vid">
    <div class="corner tl"></div><div class="corner tr"></div>
    <div class="corner bl"></div><div class="corner br"></div>
    <div class="livebadge">● REC LIVE</div>
    <div class="vinfo" id="vinfo">CAM-01 // INITIALIZING...</div>
    <div class="offline-overlay" id="offlay">
      <div>⚠ STREAM OFFLINE</div>
      <div style="font-size:.65rem;color:#888">Run multiple_tracking.py</div>
    </div>
  </div>

  <!-- SIDE PANEL -->
  <div class="spanel">
    <div class="psec">
      <div class="phdr"><div class="dot dot-g"></div>IDENTIFIED PERSONS</div>
      <div class="pbody" id="kList"><div class="empty">NO KNOWN FACES DETECTED</div></div>
    </div>
    <div class="psec">
      <div class="phdr"><div class="dot dot-r"></div>UNKNOWN INTRUDERS</div>
      <div class="pbody" id="uList"><div class="empty">AREA CLEAR</div></div>
    </div>
    <div class="psec grow">
      <div class="phdr"><div class="dot dot-y"></div>DETECTION LOG</div>
      <div class="alist" id="aList"><div class="empty">AWAITING DETECTIONS...</div></div>
    </div>
  </div>
</div>

<script>
// Clock
setInterval(()=>document.getElementById('clock').textContent=new Date().toLocaleTimeString('en-US',{hour12:false}),1000);

// Card builders
function knownCard(p){
  const c=p.coords;
  return \`<div class="card known">
    <span class="badge bg">CLEARED</span>
    <div class="fname g">\${p.name}</div>
    <div class="cgrid">
      <div class="ci"><span class="ck">X</span><span class="cv">\${c.x}px</span></div>
      <div class="ci"><span class="ck">Y</span><span class="cv">\${c.y}px</span></div>
      <div class="ci"><span class="ck">W</span><span class="cv">\${c.w}px</span></div>
      <div class="ci"><span class="ck">H</span><span class="cv">\${c.h}px</span></div>
      <div class="ci"><span class="ck">CX</span><span class="cv">\${c.center_x}</span></div>
      <div class="ci"><span class="ck">CY</span><span class="cv">\${c.center_y}</span></div>
    </div></div>\`;
}
function scanCard(p){
  const c=p.coords;
  return \`<div class="card scan">
    <span class="badge by">SCANNING</span>
    <div class="fname y">ANALYZING...</div>
    <div class="cgrid">
      <div class="ci"><span class="ck">X</span><span class="cv">\${c.x}px</span></div>
      <div class="ci"><span class="ck">Y</span><span class="cv">\${c.y}px</span></div>
      <div class="ci"><span class="ck">W</span><span class="cv">\${c.w}px</span></div>
      <div class="ci"><span class="ck">H</span><span class="cv">\${c.h}px</span></div>
      <div class="ci"><span class="ck">CX</span><span class="cv">\${c.center_x}</span></div>
      <div class="ci"><span class="ck">CY</span><span class="cv">\${c.center_y}</span></div>
    </div></div>\`;
}
function unkCard(u,i){
  return \`<div class="card unk">
    <span class="badge br2">THREAT</span>
    <div class="fname r">INTRUDER #\${i+1}</div>
    <div class="cgrid">
      <div class="ci"><span class="ck">X</span><span class="cv">\${u.x}px</span></div>
      <div class="ci"><span class="ck">Y</span><span class="cv">\${u.y}px</span></div>
      <div class="ci"><span class="ck">W</span><span class="cv">\${u.w}px</span></div>
      <div class="ci"><span class="ck">H</span><span class="cv">\${u.h}px</span></div>
      <div class="ci"><span class="ck">CX</span><span class="cv">\${u.center_x}</span></div>
      <div class="ci"><span class="ck">CY</span><span class="cv">\${u.center_y}</span></div>
    </div></div>\`;
}

let lastAlertLen=0, errCount=0;

async function poll(){
  try{
    const r=await fetch('/data',{cache:'no-store'});
    if(!r.ok) throw new Error();
    const d=await r.json();
    errCount=0;

    // System indicator
    const offline=d._offline;
    document.getElementById('sdot').className='dot '+(offline?'dot-r':'dot-g');
    document.getElementById('stxt').textContent=offline?'RECOGNITION OFFLINE':'SYSTEM ONLINE';

    // Stats
    document.getElementById('sT').textContent=d.counts?.total??0;
    document.getElementById('sK').textContent=d.counts?.known??0;
    document.getElementById('sU').textContent=d.counts?.unknown??0;
    document.getElementById('sL').textContent=new Date(d.timestamp*1000).toLocaleTimeString('en-US',{hour12:false});

    // Video info
    document.getElementById('vinfo').textContent=
      \`CAM-01 // FACES: \${d.counts?.total??0} // \${new Date().toLocaleTimeString('en-US',{hour12:false})}\`;

    // Known panel
    const kEl=document.getElementById('kList');
    const knownP=(d.known||[]).filter(p=>p.name!=='SCANNING...');
    const scanP =(d.known||[]).filter(p=>p.name==='SCANNING...');
    kEl.innerHTML=(knownP.length+scanP.length===0)
      ?'<div class="empty">NO KNOWN FACES DETECTED</div>'
      :knownP.map(knownCard).join('')+scanP.map(scanCard).join('');

    // Unknown panel
    const uEl=document.getElementById('uList');
    uEl.innerHTML=(!d.unknown||d.unknown.length===0)
      ?'<div class="empty">AREA CLEAR</div>'
      :d.unknown.map(unkCard).join('');

    // Alert log — only re-render on new entries
    if(d.alerts&&d.alerts.length!==lastAlertLen){
      lastAlertLen=d.alerts.length;
      const aEl=document.getElementById('aList');
      aEl.innerHTML=[...d.alerts].reverse().map(a=>
        \`<div class="aitem \${a.type==='KNOWN'?'ka':'ua'}">
          <span class="at">\${a.time}</span>
          <span>[\${a.type}]</span>
          <span class="an">\${a.name}</span>
        </div>\`).join('')||'<div class="empty">AWAITING DETECTIONS...</div>';
      aEl.scrollTop=0;
    }

  }catch(e){
    errCount++;
    if(errCount>4){
      document.getElementById('sdot').className='dot dot-r';
      document.getElementById('stxt').textContent='RECOGNITION OFFLINE';
    }
  }
}

// Poll every 250ms — live coordinate updates, no page refresh ever needed
setInterval(poll,250);
poll();
</script>
</body>
</html>`));

app.listen(8080,()=>{
  console.log("╔══════════════════════════════════════════════╗");
  console.log("║   NEXUS → http://localhost:8080              ║");
  console.log("╠══════════════════════════════════════════════╣");
  console.log("║   GET /       Full surveillance dashboard    ║");
  console.log("║   GET /live   Annotated live video           ║");
  console.log("║   GET /data   JSON face + coordinate data    ║");
  console.log("╚══════════════════════════════════════════════╝");
  console.log("\n  Run multiple_tracking.py first!\n");
});