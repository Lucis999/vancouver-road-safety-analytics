"""Create an isolated Mobile v2 preview from the working gh-pages HTML.

This does NOT publish or change the live website.
"""
from pathlib import Path
import re

page = Path("index.html")
html = page.read_text(encoding="utf-8")
assert all(f'id="{x}"' in html or f"id='{x}'" in html for x in ("pk-panel", "pk-ranking", "pk-collision"))
assert "</head>" in html and "</body>" in html
# Remove only known injected components, preserving the dashboard itself.
html = re.sub(r'<!-- MOBILE-RESPONSIVE-V1 START -->\\s*', '', html, count=1)
html = re.sub(r'<!-- MOBILE-RESPONSIVE-V1 END -->\\s*', '', html, count=1)
html = re.sub(r'<style id="mobile-responsive-v1">.*?</style>', '', html, count=1, flags=re.S)
html = re.sub(r'<div id="pk-mobile-toolbar"\b.*?</div>', '', html, count=1, flags=re.S)
html = re.sub(r'<div id="pk-mobile-map-options"\b.*?</div>', '', html, count=1, flags=re.S)
html = re.sub(r'<script id="pk-mobile-interaction">.*?</script>', '', html, count=1, flags=re.S)

css = """
<style id="mobile-v2-preview">
@media (min-width:761px) {#pk-mobile-v2-toolbar{display:none!important}}
#pk-mobile-v2-toolbar{display:none}
@media (max-width:760px){
 html,body{margin:0!important;max-width:100%!important;overflow-x:hidden!important;overflow-y:auto!important}
 #pk-mobile-v2-toolbar{display:flex!important;position:relative!important;box-sizing:border-box;
   height:58px;gap:6px;padding:7px 10px;background:#edf3f8;z-index:10020}
 #pk-mobile-v2-toolbar button{flex:1;min-width:0;min-height:44px;border-radius:9px;
   border:1px solid #94a3b8;background:white;color:#172033;font:600 14px Arial}
 #pk-mobile-v2-toolbar button[aria-expanded=true]{background:#0f766e;color:white}
 .folium-map,.leaflet-container{box-sizing:border-box!important}
 .folium-map{position:relative!important;inset:auto!important;left:auto!important;top:auto!important;
   width:100%!important;height:80dvh!important;min-height:320px!important;max-height:80dvh!important;
   overflow:hidden!important;touch-action:pan-x pan-y!important}
 .folium-map .leaflet-control-zoom{position:absolute!important;left:8px!important;top:50%!important;
   transform:translateY(-50%)!important;margin:0!important}
 .folium-map .leaflet-top.leaflet-left{top:0!important;bottom:0!important;pointer-events:none}
 .folium-map .leaflet-top.leaflet-left .leaflet-control{pointer-events:auto}
 #pk-panel,#pk-ranking,#pk-collision{box-sizing:border-box!important;position:fixed!important;
   left:10px!important;right:10px!important;width:auto!important;max-width:none!important;
   z-index:10015!important;overflow:auto!important;overscroll-behavior:contain!important;
   -webkit-overflow-scrolling:touch!important;border-radius:12px!important;
   box-shadow:0 6px 24px #0004!important}
 #pk-panel,#pk-ranking{top:calc(env(safe-area-inset-top,0px) + 68px)!important;
   bottom:auto!important;max-height:70dvh!important}
 #pk-collision{top:auto!important;bottom:calc(env(safe-area-inset-bottom,0px) + 12px)!important;
   height:auto!important;max-height:60dvh!important}
 #pk-panel:not(.pk-v2-open),#pk-ranking:not(.pk-v2-open),#pk-collision:not(.pk-v2-open){display:none!important}
 #pk-panel select,#pk-ranking select,#pk-collision select{max-width:100%!important;font-size:16px!important}
 #pk-panel button,#pk-ranking button,#pk-collision button{min-height:38px}
 /* Mobile collision details: replace desktop horizontal grids with one column. */
 #pk-collision{overflow-x:hidden!important;overflow-y:auto!important;padding:14px!important;
   min-height:0!important;max-height:60dvh!important}
 #pk-collision-content{width:100%!important;max-width:100%!important;min-width:0!important;
   overflow-x:hidden!important;overflow-wrap:anywhere!important}
 #pk-collision-content > div[style*="display:grid"]{display:grid!important;
   grid-template-columns:minmax(0,1fr)!important;gap:9px!important;width:100%!important}
 #pk-collision-content > div[style*="display:grid"] > *{min-width:0!important;
   max-width:100%!important;box-sizing:border-box!important}
 #pk-collision-content section{min-width:0!important;max-width:100%!important;
   width:100%!important;box-sizing:border-box!important}
 #pk-collision-content section div[style*="display:flex"]{min-width:0!important;
   flex-wrap:wrap!important;row-gap:3px!important}
 #pk-collision-content section div[style*="display:flex"] > span{min-width:0!important;
   overflow-wrap:anywhere!important;flex:1 1 60%!important}
 #pk-collision-content section div[style*="display:flex"] > b{flex:0 0 auto!important;
   white-space:nowrap!important}
 #pk-collision-content > div[style*="display:grid"] > div[style*="background:#f1f5f9"]{
   display:flex!important;justify-content:space-between!important;align-items:center!important;
   gap:10px!important;padding:11px 12px!important}
 #pk-collision-content > div[style*="display:grid"] > div[style*="background:#f1f5f9"] > div{
   min-width:0!important}

}
</style>
"""
toolbar = """<nav id="pk-mobile-v2-toolbar" aria-label="Dashboard panels">
<button type="button" data-panel="pk-panel" aria-expanded="false">Filters</button>
<button type="button" data-panel="pk-ranking" aria-expanded="false">Top 10</button>
<button type="button" data-panel="pk-collision" aria-expanded="false">Collisions</button>
</nav>"""
js = """
<script id="pk-mobile-v2-interaction">
(function(){
 function init(){
  var nav=document.getElementById('pk-mobile-v2-toolbar');
  if(!nav)return;
  var buttons=Array.from(nav.querySelectorAll('button[data-panel]'));
  function show(id){
   buttons.forEach(function(b){
    var active=b.dataset.panel===id, p=document.getElementById(b.dataset.panel);
    b.setAttribute('aria-expanded',String(active));
    if(p)p.classList.toggle('pk-v2-open',active);
   });
  }
  buttons.forEach(function(b){b.addEventListener('click',function(){
   show(b.getAttribute('aria-expanded')==='true'?'':b.dataset.panel);
  })});
  show('');
  document.addEventListener('keydown',function(e){if(e.key==='Escape')show('')});
  var mq=window.matchMedia('(max-width:760px)');
  if(mq.addEventListener)mq.addEventListener('change',function(){show('')});
  function resizeMap(){
   Object.keys(window).filter(function(k){return /^map_[a-zA-Z0-9_]+$/.test(k)}).forEach(function(k){
    var m=window[k];if(m&&typeof m.invalidateSize==='function')m.invalidateSize();
   });
  }
  window.addEventListener('resize',resizeMap);
  setTimeout(resizeMap,250);
  setTimeout(resizeMap,1200);
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);
 else init();
})();
</script>
"""
html = html.replace("</head>",css+"</head>",1)
html = html.replace("<body>", "<body>"+toolbar,1) if "<body>" in html else html.replace("</body>",toolbar+"</body>",1)
html = html.replace("</body>",js+"</body>",1)
assert html.count('id="pk-mobile-v2-toolbar"') == 1
assert html.count('id="mobile-v2-preview"') == 1
page.write_text(html,encoding="utf-8")
print("Mobile v2 preview generated:",page.stat().st_size,"bytes")
