from pathlib import Path
import re

page = Path("index.html")
html = page.read_text(encoding="utf-8")
start = "<!-- MOBILE-RESPONSIVE-V1 START -->"
end = "<!-- MOBILE-RESPONSIVE-V1 END -->"
if start in html and end in html:
    html = html[:html.index(start)] + html[html.index(end)+len(end):]
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
 #pk-panel select,#pk-ranking select,#pk-collision select{max-width:100%!important;font-size:16px!important}
 #pk-panel button,#pk-ranking button,#pk-collision button{min-height:38px}
 #pk-panel input[type=checkbox],#pk-collision input[type=checkbox]{min-width:18px;min-height:18px}
}
@media(min-width:761px){#pk-mobile-toolbar{display:none!important}}
#pk-mobile-toolbar{display:none;position:fixed;top:calc(env(safe-area-inset-top,0px) + 8px);
 left:10px;right:10px;z-index:10020;gap:7px;pointer-events:none}
#pk-mobile-toolbar button{pointer-events:auto;flex:1;min-width:0;padding:11px 5px;
 border:1px solid #94a3b8;border-radius:10px;background:white;color:#172033;
 font:600 13px Arial,sans-serif;box-shadow:0 2px 10px #0003}
#pk-mobile-toolbar button[aria-expanded=true]{background:#0f766e;color:white;border-color:#0f766e}
</style>
"""
toolbar = """<div id="pk-mobile-toolbar" role="group" aria-label="Dashboard panels">
<button type="button" data-pk-target="pk-panel" aria-controls="pk-panel" aria-expanded="false">Filters</button>
<button type="button" data-pk-target="pk-ranking" aria-controls="pk-ranking" aria-expanded="false">Top 10</button>
<button type="button" data-pk-target="pk-collision" aria-controls="pk-collision" aria-expanded="false">Collisions</button>
</div>"""
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
