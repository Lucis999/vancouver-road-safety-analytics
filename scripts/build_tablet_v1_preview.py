"""Generate isolated iPad/tablet preview from published dashboard HTML."""
from pathlib import Path

page=Path("index.html")
html=page.read_text(encoding="utf-8")
assert all(('id="'+x+'"') in html or ("id='"+x+"'") in html for x in ("pk-panel","pk-ranking","pk-collision"))
assert "</head>" in html and "</body>" in html
css="""
<style id="tablet-v1-styles">
#pk-tablet-collapse{display:none}
@media (min-width:761px) and (max-width:1199px) and (pointer:coarse){
 #pk-panel{width:clamp(245px,25vw,320px)!important;max-width:32vw!important}
 #pk-ranking{width:clamp(245px,26vw,330px)!important;max-width:33vw!important}
 #pk-collision{box-sizing:border-box!important;left:12px!important;right:12px!important;
   width:auto!important;bottom:12px!important;max-height:55dvh!important;
   overflow-y:auto!important;overflow-x:hidden!important;
   -webkit-overflow-scrolling:touch!important;overscroll-behavior:contain!important;
   padding-top:46px!important;transition:none!important}
 #pk-collision.pk-tablet-collapsed{height:64px!important;min-height:64px!important;
   max-height:64px!important;overflow:hidden!important}
 #pk-tablet-collapse{display:block!important;position:absolute!important;top:8px!important;
   right:12px!important;z-index:5!important;border:1px solid #94a3b8!important;
   border-radius:8px!important;padding:9px 12px!important;min-height:40px!important;
   background:#fff!important;color:#172033!important;font-weight:600!important;
   cursor:pointer!important}
 #pk-collision-content{max-width:100%!important;overflow-x:hidden!important}
 #pk-collision.pk-tablet-collapsed #pk-collision-content{visibility:hidden!important}
 #pk-collision select,#pk-collision button{min-height:36px}
}
</style>
"""
js="""
<script id="tablet-v1-interaction">
(function(){
 function init(){
  var panel=document.getElementById('pk-collision');
  if(!panel)return;
  var button=document.createElement('button');
  button.type='button';button.id='pk-tablet-collapse';
  button.setAttribute('aria-controls','pk-collision-content');
  panel.insertBefore(button,panel.firstChild);
  var mq=window.matchMedia('(min-width:761px) and (max-width:1199px) and (pointer:coarse)');
  function sync(){
   if(mq.matches){
    if(!panel.dataset.tabletInitialized){
     panel.classList.add('pk-tablet-collapsed');
     panel.dataset.tabletInitialized='1';
    }
   }else{
    panel.classList.remove('pk-tablet-collapsed');
    delete panel.dataset.tabletInitialized;
   }
   var collapsed=panel.classList.contains('pk-tablet-collapsed');
   button.textContent=collapsed?'Expand collision details':'Collapse collision details';
   button.setAttribute('aria-expanded',String(!collapsed));
  }
  button.addEventListener('click',function(){
   panel.classList.toggle('pk-tablet-collapsed');
   sync();
  });
  if(mq.addEventListener)mq.addEventListener('change',sync);
  sync();
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);
 else init();
})();
</script>
"""
html=html.replace("</head>",css+"</head>",1)
html=html.replace("</body>",js+"</body>",1)
assert html.count('id="tablet-v1-styles"')==1
page.write_text(html,encoding="utf-8")
print("Tablet preview created",page.stat().st_size)
