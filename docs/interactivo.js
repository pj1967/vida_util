
(function(){
  var $=function(s,c){return (c||document).querySelector(s)};
  var $$=function(s,c){return Array.prototype.slice.call((c||document).querySelectorAll(s))};

  function hace(iso){
    var d=new Date(iso); if(isNaN(d)) return null;
    var s=(Date.now()-d.getTime())/1000;
    if(s<0) return null;
    if(s<3600) return 'hace '+Math.max(1,Math.round(s/60))+' min';
    if(s<86400) return 'hace '+Math.round(s/3600)+' h';
    var dias=Math.round(s/86400);
    if(dias<=6) return 'hace '+dias+(dias===1?' día':' días');
    return null;
  }
  $$('time[data-iso]').forEach(function(t){
    var h=hace(t.getAttribute('data-iso')); if(h) t.textContent=h;
  });

  var flujo=$('#flujo'), caja=$('#buscar');
  if(flujo){
    var items=$$('li.item',flujo), paso=15, visibles=paso, tema='todas', q='', horas=0;
    var mas=$('#mas'), vacio=$('#sin-resultados');
    var pintar=function(){
      var coinc=items.filter(function(li){
        var ts=parseInt(li.getAttribute('data-ts')||'0',10)*1000;
        return (tema==='todas'||li.getAttribute('data-tema')===tema) &&
               (!horas||(ts&&Date.now()-ts<=horas*3600000)) &&
               (!q||li.textContent.toLowerCase().indexOf(q)>-1);
      });
      items.forEach(function(li){li.classList.add('oculto');});
      coinc.slice(0,visibles).forEach(function(li){li.classList.remove('oculto');});
      if(mas) mas.classList.toggle('oculto',coinc.length<=visibles);
      if(vacio) vacio.classList.toggle('oculto',coinc.length>0);
    };
    $$('.chip-tema').forEach(function(b){
      b.addEventListener('click',function(){
        tema=b.getAttribute('data-tema'); visibles=paso;
        $$('.chip-tema').forEach(function(x){x.classList.toggle('activo',x===b);});
        pintar();
      });
    });
    $$('.chip-tiempo').forEach(function(b){
      b.addEventListener('click',function(){
        horas=parseInt(b.getAttribute('data-horas'),10)||0; visibles=paso;
        $$('.chip-tiempo').forEach(function(x){x.classList.toggle('activo',x===b);});
        pintar();
      });
    });
    if(caja) caja.addEventListener('input',function(){q=caja.value.toLowerCase().trim();visibles=paso;pintar();});
    if(mas) mas.addEventListener('click',function(){visibles+=paso;pintar();});
    pintar();
  } else if(caja){
    caja.addEventListener('input',function(){
      var q=caja.value.toLowerCase().trim();
      $$('li.item').forEach(function(li){
        li.classList.toggle('oculto', !!q && li.textContent.toLowerCase().indexOf(q)===-1);
      });
      $$('section.bloque').forEach(function(s){
        s.classList.toggle('oculto', !!q && !s.querySelector('li.item:not(.oculto)'));
      });
    });
  }

  document.addEventListener('keydown',function(e){
    var activo=document.activeElement, tag=activo?activo.tagName:'';
    if(e.key==='/' && !/INPUT|TEXTAREA/.test(tag) && caja){e.preventDefault();caja.focus();}
    if(e.key==='Escape' && caja && activo===caja){caja.blur();}
  });
  document.addEventListener('click',function(e){
    $$('details.desplegable').forEach(function(d){ if(!d.contains(e.target)) d.removeAttribute('open'); });
  });

  /* Visor de PDF dentro de la página */
  var visor=null;
  function crearVisor(){
    visor=document.createElement('dialog'); visor.className='visor';
    visor.innerHTML='<div class="visor-barra"><span class="visor-titulo"></span>'+
      '<a class="visor-nueva" target="_blank" rel="noopener noreferrer">Abrir en pestaña nueva</a>'+
      '<button type="button" class="visor-cerrar" aria-label="Cerrar">Cerrar ✕</button></div>'+
      '<div class="visor-marco"></div>';
    document.body.appendChild(visor);
    $('.visor-cerrar',visor).addEventListener('click',function(){visor.close();});
    visor.addEventListener('click',function(e){ if(e.target===visor) visor.close(); });
    visor.addEventListener('close',function(){ $('.visor-marco',visor).innerHTML=''; });
  }
  document.addEventListener('click',function(e){
    var a=e.target.closest ? e.target.closest('a.ver-pdf') : null;
    if(!a || e.ctrlKey || e.metaKey || e.shiftKey || e.button>0) return;
    if(typeof HTMLDialogElement==='undefined') return;
    e.preventDefault();
    if(!visor) crearVisor();
    $('.visor-titulo',visor).textContent=a.textContent;
    $('.visor-nueva',visor).setAttribute('href',a.getAttribute('href'));
    var marco=$('.visor-marco',visor); marco.innerHTML='';
    var f=document.createElement('iframe');
    f.setAttribute('title',a.textContent); f.setAttribute('src',a.getAttribute('href'));
    marco.appendChild(f);
    if(!visor.open) visor.showModal();
  });
})();
