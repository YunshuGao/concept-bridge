"""HTML templates for the ConceptBridge static site. Stdlib only."""
import json as _json
from html import escape

CSS = """
:root { --ink:#1a1a2e; --acc:#b4373a; --acc2:#1f6f8b; --bg:#faf8f4; --card:#ffffff;
        --muted:#6b6b7b; --line:#e5e0d8; }
* { box-sizing:border-box; margin:0; }
body { font-family:'Segoe UI', 'Microsoft YaHei', 'PingFang SC', sans-serif;
       background:var(--bg); color:var(--ink); line-height:1.65; }
header { background:var(--ink); color:#fff; padding:.8rem 1.2rem;
         display:flex; gap:1rem; align-items:center; flex-wrap:wrap; position:relative; }
header a { color:#fff; text-decoration:none; font-weight:600; }
header .crumb { color:#bbb; font-weight:400; font-size:.9rem; }
#q { flex:1; min-width:180px; max-width:420px; padding:.45rem .7rem;
     border-radius:6px; border:none; font-size:1rem; }
#results { position:absolute; top:3.4rem; right:1.2rem; left:auto; width:min(480px,90vw);
           background:var(--card); border:1px solid var(--line); border-radius:8px;
           box-shadow:0 8px 24px rgba(0,0,0,.18); max-height:60vh; overflow:auto; z-index:9; }
#results a { display:block; padding:.55rem .8rem; color:var(--ink);
             text-decoration:none; border-bottom:1px solid var(--line); }
#results a:hover { background:var(--bg); }
main { max-width:920px; margin:0 auto; padding:1.4rem 1.2rem 4rem; }
h1 { font-size:1.7rem; margin:.8rem 0 .3rem; }
h1 .en { color:var(--acc2); display:block; font-size:1.15rem; font-weight:600; }
h2 { font-size:1.05rem; color:var(--acc); margin:1.5rem 0 .5rem;
     text-transform:uppercase; letter-spacing:.06em; }
.card { background:var(--card); border:1px solid var(--line); border-radius:10px;
        padding:1rem 1.2rem; margin:.6rem 0; }
.zh { font-size:1.02rem; } .endef { color:var(--acc2); margin-top:.3rem; }
.pinyin { color:var(--muted); font-style:italic; font-size:1rem; }
.tag { display:inline-block; background:#eee7db; border-radius:99px; padding:.1rem .7rem;
       font-size:.82rem; margin:.15rem .25rem .15rem 0; color:var(--ink);
       text-decoration:none; }
.nuance { border-left:4px solid var(--acc); background:#fdf1f1; }
ul.plain { list-style:none; padding:0; } ul.plain li { padding:.2rem 0; }
.rel { color:var(--muted); font-size:.85rem; margin-right:.4rem; }
a.node { color:var(--acc2); text-decoration:none; font-weight:600; }
a.node:hover { text-decoration:underline; }
.grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(240px,1fr)); gap:.6rem; }
.grid .card { margin:0; }
.meta { color:var(--muted); font-size:.88rem; }
footer { text-align:center; color:var(--muted); font-size:.85rem; padding:2rem 0; }
canvas { width:100%; background:var(--card); border:1px solid var(--line); border-radius:10px; }
.count { color:var(--muted); font-weight:400; font-size:1rem; }
"""

SEARCH_JS = """
const box=document.getElementById('q'),res=document.getElementById('results');
let IDX=null;
async function idx(){ if(!IDX){ const r=await fetch(ROOT+'search-index.json');
  IDX=await r.json(); } return IDX; }
box&&box.addEventListener('input',async()=>{
  const q=box.value.trim().toLowerCase();
  if(!q){res.style.display='none';return;}
  const d=await idx();
  const hits=d.filter(e=>e.t.some(t=>t.includes(q))).slice(0,20);
  res.innerHTML=hits.map(e=>`<a href="${ROOT}c/${e.id}.html"><b>${e.zh}</b> · ${e.en}</a>`).join('')
    ||'<a>无结果 · no results</a>';
  res.style.display='block';
});
document.addEventListener('click',e=>{ if(res&&!res.contains(e.target)&&e.target!==box)
  res.style.display='none'; });
"""

GRAPH_JS = """
const cv=document.getElementById('g'),ctx=cv.getContext('2d');
const W=cv.width=cv.clientWidth*devicePixelRatio,H=cv.height=560*devicePixelRatio;
const N=GDATA.nodes.map((n,i)=>({...n,x:Math.random()*W,y:Math.random()*H,vx:0,vy:0}));
const byId=Object.fromEntries(N.map(n=>[n.id,n]));
const E=GDATA.edges.filter(e=>byId[e.s]&&byId[e.t]);
function step(){
  for(const a of N){a.vx*=.6;a.vy*=.6;
    for(const b of N){ if(a===b)continue;
      let dx=a.x-b.x,dy=a.y-b.y,d2=dx*dx+dy*dy+40;const f=1800*devicePixelRatio/d2;
      a.vx+=dx*f/Math.sqrt(d2);a.vy+=dy*f/Math.sqrt(d2);}
    a.vx+=(W/2-a.x)*.0012;a.vy+=(H/2-a.y)*.0012;}
  for(const e of E){const s=byId[e.s],t=byId[e.t];
    const dx=t.x-s.x,dy=t.y-s.y,d=Math.sqrt(dx*dx+dy*dy)||1,f=(d-90*devicePixelRatio)*.004;
    s.vx+=dx/d*f;s.vy+=dy/d*f;t.vx-=dx/d*f;t.vy-=dy/d*f;}
  for(const n of N){n.x+=n.vx;n.y+=n.vy;
    n.x=Math.max(20,Math.min(W-20,n.x));n.y=Math.max(20,Math.min(H-20,n.y));}
}
function draw(){
  ctx.clearRect(0,0,W,H);ctx.strokeStyle='#d8d2c6';
  for(const e of E){const s=byId[e.s],t=byId[e.t];
    ctx.beginPath();ctx.moveTo(s.x,s.y);ctx.lineTo(t.x,t.y);ctx.stroke();}
  ctx.font=`${11*devicePixelRatio}px sans-serif`;ctx.textAlign='center';
  for(const n of N){ctx.fillStyle='#1f6f8b';
    ctx.beginPath();ctx.arc(n.x,n.y,5*devicePixelRatio,0,7);ctx.fill();
    ctx.fillStyle='#1a1a2e';ctx.fillText(n.zh,n.x,n.y-9*devicePixelRatio);}
}
let ticks=0;(function loop(){step();draw();if(++ticks<400)requestAnimationFrame(loop);})();
cv.addEventListener('click',ev=>{
  const r=cv.getBoundingClientRect();
  const x=(ev.clientX-r.left)*devicePixelRatio,y=(ev.clientY-r.top)*devicePixelRatio;
  for(const n of N){ if((n.x-x)**2+(n.y-y)**2<180*devicePixelRatio)location.href='c/'+n.id+'.html';}
});
"""


def page(title, body, root="", crumb=""):
    """root: relative prefix back to site root, e.g. '' or '../'."""
    return f"""<!DOCTYPE html>
<html lang="zh-Hans">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} · ConceptBridge</title>
<style>{CSS}</style>
</head>
<body>
<header>
  <a href="{root}index.html">概念桥 ConceptBridge</a>
  <span class="crumb">{crumb}</span>
  <input id="q" type="search" placeholder="搜索 search: 科举 / keju / examination…"
         autocomplete="off">
  <div id="results" style="display:none"></div>
</header>
<main>
{body}
</main>
<footer>ConceptBridge · 中英概念网络 · generated by build.py</footer>
<script>const ROOT="{root}";{SEARCH_JS}</script>
</body>
</html>"""


def graph_page(nodes):
    data = {
        "nodes": [{"id": n["id"], "zh": n["zh"]} for n in nodes],
        "edges": [{"s": n["id"], "t": l["to"]}
                  for n in nodes for l in n.get("links", [])],
    }
    body = ("<h1>网络图 <span class='en'>Concept graph — click a node</span></h1>"
            "<canvas id='g' style='height:560px'></canvas>"
            f"<script>const GDATA={_json.dumps(data, ensure_ascii=False)};{GRAPH_JS}</script>")
    return page("Graph", body)
