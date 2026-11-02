from pathlib import Path
import re

page = Path("index.html")
html = page.read_text(encoding="utf-8")
start = "<!-- MOBILE-RESPONSIVE-V1 START -->"
end = "<!-- MOBILE-RESPONSIVE-V1 END -->"
# Remove only the previously injected CSS and controls. Never remove the
# intervening dashboard markup between </head> and </body>.
if start in html or end in html:
    assert start in html and end in html, "Incomplete previous mobile patch"
    css_start = html.index(start)
    css_end_tag = "</style>"
    css_end = html.index(css_end_tag, css_start) + len(css_end_tag)
    html = html[:css_start] + html[css_end:]
    html = html.replace(end, "", 1)
    html = re.sub(r'<div id="pk-mobile-toolbar"\\b.*?</div>', "", html, count=1, flags=re.S)
    html = re.sub(r'<div id="pk-mobile-map-options"\\b.*?</div>', "", html, count=1, flags=re.S)
    html = re.sub(r'<script id="pk-mobile-interaction">.*?</script>', "", html, count=1, flags=re.S)
# An older patch may have injected its CSS/JS without the current marker layout.
html = re.sub(r'<style id="mobile-responsive-v1">.*?</style>', "", html, count=1, flags=re.S)
css = r"""
<style id="mobile-responsive-v1">
@media (max-width: 760px) {
 html,body{width:100%!important;max-width:100%!important;overflow-x:hidden!important}
 #pk-mobile-toolbar{display:flex!important}
 #pk-panel,#pk-ranking,#pk-collision{
   box-sizing:border-box!important;position:fixed!important;
   left:10px!important;right:10px!important;width:auto!important;
   max-width:none!important;z-index:10010!important;
   border-radius:12px!important;box-shadow:0 8px 28px #0004!important;
 }
 #pk-panel,#pk-ranking{top:calc(env(safe-area-inset-top,0px) + 62px)!important;
   bottom:auto!important;max-height:calc(100dvh - 95px)!important;overflow-y:auto!important}
 #pk-collision{top:auto!important;bottom:calc(env(safe-area-inset-bottom,0px) + 12px)!important;
   height:auto!important;max-height:58dvh!important;overflow-y:auto!important}
 #pk-panel:not(.pk-mobile-open),#pk-ranking:not(.pk-mobile-open),
 #pk-collision:not(.pk-mobile-open){display:none!important}
 #pk-panel select,#pk-ranking select,#pk-collision select{max-width:100%!important;font-size:16px!important}\n #pk-panel,#pk-ranking,#pk-collision{overscroll-behavior:contain;-webkit-overflow-scrolling:touch}\n #pk-mobile-toolbar button{min-height:46px}
 #pk-panel button,#pk-ranking button,#pk-collision button{min-height:38px}
 #pk-panel input[type=checkbox],#pk-collision input[type=checkbox]{min-width:18px;min-height:18px}
}
@media(min-width:761px){#pk-mobile-toolbar{display:none!important}}
#pk-mobile-toolbar{display:none;position:fixed;top:calc(env(safe-area-inset-top,0px) + 8px);
 left:10px;right:10px;z-index:10020;gap:7px;pointer-events:none}
#pk-mobile-toolbar button{pointer-events:auto;flex:1;min-width:0;padding:11px 5px;
 border:1px solid #94a3b8;border-radius:10px;background:white;color:#172033;
 font:600 13px Arial,sans-serif;box-shadow:0 2px 10px #0003}
#pk-mobile-toolbar button[aria-expanded=true]{background:#0f766e;color:white;border-color:#0f766e}\n#pk-mobile-toolbar button:focus-visible{outline:3px solid #14b8a6;outline-offset:2px}\n#pk-mobile-map-options{display:none;position:fixed;bottom:calc(env(safe-area-inset-bottom,0px) + 20px);left:12px;z-index:10005;gap:6px}\n@media(max-width:760px){#pk-mobile-map-options{display:flex}}\n#pk-mobile-map-options button{border:1px solid #94a3b8;border-radius:9px;padding:9px 12px;background:white;color:#172033;font:600 12px Arial;box-shadow:0 2px 9px #0003}\n#pk-mobile-map-options button[aria-pressed=true]{background:#0f766e;color:white}
</style>
"""
toolbar = """<div id="pk-mobile-toolbar" role="group" aria-label="Dashboard panels">
<button type="button" data-pk-target="pk-panel" aria-controls="pk-panel" aria-expanded="false">Filters</button>
<button type="button" data-pk-target="pk-ranking" aria-controls="pk-ranking" aria-expanded="false">Top 10</button>
<button type="button" data-pk-target="pk-collision" aria-controls="pk-collision" aria-expanded="false">Collisions</button>
</div><div id="pk-mobile-map-options"><button type="button" id="pk-basemap-toggle" aria-pressed="false">Street map: Off</button></div>"""
js = r"""<script id="pk-mobile-interaction">
(function(){
 function init(){
  var toolbar=document.getElementById('pk-mobile-toolbar');
  if(!toolbar)return;
  var buttons=Array.from(toolbar.querySelectorAll('button[data-pk-target]'));
  function toggle(id){
   buttons.forEach(function(b){
    var open=b.dataset.pkTarget===id;
    var panel=document.getElementById(b.dataset.pkTarget);
    b.setAttribute('aria-expanded',String(open));
    if(panel)panel.classList.toggle('pk-mobile-open',open);
   });
  }
  buttons.forEach(function(b){b.addEventListener('click',function(){
   toggle(b.getAttribute('aria-expanded')==='true'?'':b.dataset.pkTarget);
  })});
  toggle('');
  // Mobile: touch a road to select its location, rather than relying on hover.
  // Existing road click listeners are preserved.
  document.addEventListener('keydown',function(e){if(e.key==='Escape')toggle('')});
  document.querySelectorAll('.leaflet-container').forEach(function(el){
   el.addEventListener('click',function(e){
    if(window.matchMedia('(max-width:760px)').matches && !e.target.closest('#pk-panel,#pk-ranking,#pk-collision,#pk-mobile-toolbar'))toggle('');
   });
  });
  var basemap=document.getElementById('pk-basemap-toggle');
  var mapInstance=null,baseLayer=null;
  function findMap(){
   if(mapInstance)return mapInstance;
   var maps=Object.keys(window).filter(function(k){return /^map_[a-zA-Z0-9_]+$/.test(k)});
   for(var i=0;i<maps.length;i++){var m=window[maps[i]];if(m&&typeof m.addLayer==='function'&&typeof m.getCenter==='function'){mapInstance=m;break}}
   return mapInstance;
  }
  if(basemap)basemap.addEventListener('click',function(){
   var m=findMap();
   if(!m||!window.L)return;
   if(!baseLayer){
    baseLayer=L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{
     attribution:'&copy; OpenStreetMap contributors',maxZoom:19,
     crossOrigin:true
    });
    baseLayer.on('tileerror',function(){basemap.textContent='Street map unavailable'});
   }
   if(m.hasLayer(baseLayer)){m.removeLayer(baseLayer);basemap.setAttribute('aria-pressed','false');basemap.textContent='Street map: Off'}
   else{baseLayer.addTo(m);baseLayer.bringToBack();basemap.setAttribute('aria-pressed','true');basemap.textContent='Street map: On'}
  });
  var mq=window.matchMedia('(max-width: 760px)');
  if(mq.addEventListener)mq.addEventListener('change',function(){toggle('')});
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);
 else init();
})();
</script>"""
for panel_id in ("pk-panel","pk-ranking","pk-collision"):
    assert re.search(r'id=["\']'+panel_id+r'["\']',html), "Missing "+panel_id
assert "</head>" in html and "</body>" in html
html=html.replace("</head>",start+css+"</head>",1)
html=html.replace("</body>",toolbar+js+end+"</body>",1)
page.write_text(html,encoding="utf-8")
print("Patched",page,"bytes:",page.stat().st_size)
