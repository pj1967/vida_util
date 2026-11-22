
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

  /* ---- progreso por pasos y test (se guarda solo en este navegador) ---- */
  function lee(k){ try{ return window.localStorage.getItem(k); }catch(e){ return null; } }
  function guarda(k,v){ try{ window.localStorage.setItem(k,v); }catch(e){} }
  function pintaProgreso(){
    var lis=$$('li[data-paso]'); if(!lis.length) return;
    var hechos=0;
    lis.forEach(function(li){
      var ok=lee('mm-ok:'+li.getAttribute('data-paso'))==='1';
      li.classList.toggle('hecho',ok); if(ok) hechos++;
    });
    var p=$('.prog'); if(!p) return;
    $('.prog-n',p).textContent=hechos;
    $('.prog-barra i',p).style.width=Math.round(100*hechos/lis.length)+'%';
  }
  pintaProgreso();
  $$('button.copiar').forEach(function(b){
    b.addEventListener('click',function(){
      var pre=b.parentNode.querySelector('pre'); if(!pre||!navigator.clipboard) return;
      navigator.clipboard.writeText(pre.textContent).then(function(){ b.textContent='Copiado ✓'; setTimeout(function(){ b.textContent='Copiar'; },1500); });
    });
  });
  var marcar=$('#marcar-paso');
  if(marcar){
    var clave=marcar.getAttribute('data-clave');
    var pinta=function(){
      var ok=lee('mm-ok:'+clave)==='1';
      marcar.textContent= ok ? '✓ Paso completado (pulsa para desmarcar)' : 'Marcar este paso como completado';
      marcar.classList.toggle('verde',ok);
    };
    pinta();
    marcar.addEventListener('click',function(){ guarda('mm-ok:'+clave, lee('mm-ok:'+clave)==='1' ? '0' : '1'); pinta(); });
  }
  var test=$('#test');
  if(test){
    var datos=JSON.parse($('#test-datos').textContent);
    var cuerpo=$('#test-cuerpo');
    var mezcla=function(a){ a=a.slice(); for(var i=a.length-1;i>0;i--){ var j=Math.floor(Math.random()*(i+1)); var t=a[i]; a[i]=a[j]; a[j]=t; } return a; };
    var texto=function(s){ var d=document.createElement('span'); d.textContent=s; return d; };
    var nuevo=function(){
      var preg=mezcla(datos.preguntas).slice(0,datos.cuantas||8);
      cuerpo.innerHTML='';
      var form=document.createElement('form');
      preg.forEach(function(q,i){
        var opts=mezcla([{t:q.ok,ok:true}].concat(q.mal.map(function(m){ return {t:m,ok:false}; })));
        var div=document.createElement('div'); div.className='pregunta';
        var p=document.createElement('p'); p.textContent=(i+1)+'. '+q.q; div.appendChild(p);
        opts.forEach(function(o){
          var l=document.createElement('label'); var r=document.createElement('input');
          r.type='radio'; r.name='q'+i; r.setAttribute('data-ok',o.ok?'1':'0');
          l.appendChild(r); l.appendChild(texto(o.t)); div.appendChild(l);
        });
        var e=document.createElement('p'); e.className='exp'; e.hidden=true; e.textContent=q.exp; div.appendChild(e);
        form.appendChild(div);
      });
      var b=document.createElement('button'); b.type='button'; b.className='boton'; b.textContent='Corregir';
      form.appendChild(b); cuerpo.appendChild(form);
      var res=document.createElement('div'); cuerpo.appendChild(res);
      b.addEventListener('click',function(){
        var bien=0, sin=0;
        $$('.pregunta',form).forEach(function(div){
          var m=$('input:checked',div);
          div.classList.remove('ok','mal');
          $$('label',div).forEach(function(l){ l.classList.remove('marcada','correcta'); if($('input',l).getAttribute('data-ok')==='1') l.classList.add('correcta'); });
          if(!m){ sin++; return; }
          m.parentNode.classList.add('marcada');
          if(m.getAttribute('data-ok')==='1'){ bien++; div.classList.add('ok'); } else div.classList.add('mal');
          $('.exp',div).hidden=false;
        });
        if(sin){ res.className='resultado regular'; res.textContent='Te faltan '+sin+' pregunta(s) por contestar.'; return; }
        var pct=Math.round(100*bien/preg.length), apr=datos.aprobado||70;
        res.innerHTML='';
        res.className='resultado '+(pct>=apr?'bien':'regular');
        res.appendChild(texto(bien+' de '+preg.length+' ('+pct+' %). '+(pct>=apr?'¡Aprobado! Ya puedes marcar el paso como completado.':'Repasa la explicación de las falladas y vuelve a intentarlo con otras preguntas.')));
        if(pct>=apr && test.getAttribute('data-clave')){ guarda('mm-test:'+test.getAttribute('data-clave'),String(pct)); }
        var r=document.createElement('button'); r.type='button'; r.className='boton'; r.textContent='Repetir con otras preguntas';
        r.addEventListener('click',nuevo); res.appendChild(document.createElement('br')); res.appendChild(r);
        b.disabled=true;
      });
    };
    nuevo();
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
