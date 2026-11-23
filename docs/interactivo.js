
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


  /* ---- laboratorio con datos reales: nube de puntos y recta ---- */
  function fmt(v,d){ return v.toLocaleString('es-ES',{minimumFractionDigits:d,maximumFractionDigits:d}); }
  function iniciaLab(box){
    var src=box.getAttribute('data-src'), modo=box.getAttribute('data-modo')||'recta';
    var cuerpo=$('.labr-cuerpo',box);
    fetch(src).then(function(r){ if(!r.ok) throw new Error('no'); return r.json(); }).then(function(D){
      var N=D.t.length, T=D.t, P=D.p, E=D.e;
      var tmin=Math.min.apply(null,T), tmax=Math.max.apply(null,T), pmin=Math.min.apply(null,P), pmax=Math.max.apply(null,P);
      var cv=$('canvas',box), cx=cv.getContext('2d');
      var sM=$('.m',box), sB=$('.b',box), vM=$('.mv',box), vB=$('.bv',box);
      var selG=$('select',box), chkPiv=$('.piv',box), chkRec=$('.rec',box);
      var mo=D.m, bo=D.b, msg=$('.labr-msg',box);
      var tr=0, xm=0, ym=0;
      for(var i=0;i<N;i++){ if(!E[i]){ tr++; xm+=T[i]; ym+=P[i]; } }
      xm/=tr; ym/=tr;
      if(modo==='recta'){
        sM.min=(mo-3).toFixed(2); sM.max=(mo+3).toFixed(2); sM.step='0.01';
        sB.min=(bo-120).toFixed(1); sB.max=(bo+120).toFixed(1); sB.step='0.1';
        sM.value=0; sB.value=ym.toFixed(1);
      }
      var cor=(function(){ var st=0,sp=0,stp=0,stt=0,spp=0,mt=0,mp=0,i; for(i=0;i<N;i++){mt+=T[i];mp+=P[i];} mt/=N; mp/=N;
        for(i=0;i<N;i++){ stp+=(T[i]-mt)*(P[i]-mp); stt+=(T[i]-mt)*(T[i]-mt); spp+=(P[i]-mp)*(P[i]-mp); } return stp/Math.sqrt(stt*spp); })();
      function sel(i){ var g=selG?selG.value:'todos'; return g==='todos' || (g==='train' && !E[i]) || (g==='test' && E[i]); }
      function calc(m,b){
        var n=0,sse=0,sae=0,sp=0,i,r;
        for(i=0;i<N;i++){ if(!sel(i)) continue; n++; sp+=P[i]; r=P[i]-(m*T[i]+b); sse+=r*r; sae+=Math.abs(r); }
        var pm=sp/n, sst=0; for(i=0;i<N;i++){ if(!sel(i)) continue; sst+=(P[i]-pm)*(P[i]-pm); }
        return {n:n,sse:sse,rmse:Math.sqrt(sse/n),mae:sae/n,r2:1-sse/sst};
      }
      var geo={};
      function dibuja(){
        var W=cv.clientWidth, H=Math.round(W*0.62), dpr=window.devicePixelRatio||1;
        cv.width=W*dpr; cv.height=H*dpr; cv.style.height=H+'px'; cx.setTransform(dpr,0,0,dpr,0,0);
        var L=54,Rr=12,Tt=12,Bb=40;
        var x0=tmin-1,x1=tmax+1,y0=pmin-6,y1=pmax+6;
        var X=function(x){ return L+(x-x0)*(W-L-Rr)/(x1-x0); }, Y=function(y){ return H-Bb-(y-y0)*(H-Tt-Bb)/(y1-y0); };
        cx.clearRect(0,0,W,H);
        cx.font='11px sans-serif'; cx.fillStyle='#8896ad'; cx.strokeStyle='#1d2b44'; cx.lineWidth=1;
        var k,v;
        for(k=0;k<=5;k++){ v=y0+(y1-y0)*k/5; cx.beginPath(); cx.moveTo(L,Y(v)); cx.lineTo(W-Rr,Y(v)); cx.stroke(); cx.textAlign='right'; cx.fillText(Math.round(v),L-6,Y(v)+4); }
        for(k=0;k<=6;k++){ v=x0+(x1-x0)*k/6; cx.textAlign='center'; cx.fillText(Math.round(v),X(v),H-Bb+16); }
        cx.fillStyle='#cbd5e1'; cx.textAlign='center'; cx.fillText('Temperatura ambiente (°C)',(L+W-Rr)/2,H-6);
        cx.save(); cx.translate(13,(Tt+H-Bb)/2); cx.rotate(-Math.PI/2); cx.fillText('Potencia (MW)',0,0); cx.restore();
        var i, g=selG?selG.value:'todos';
        for(i=0;i<N;i++){
          var on=sel(i); cx.globalAlpha=on?0.28:0.05;
          cx.fillStyle=(g==='todos' && E[i])?'#fbbf24':'#38bdf8';
          cx.beginPath(); cx.arc(X(T[i]),Y(P[i]),1.9,0,6.2832); cx.fill();
        }
        cx.globalAlpha=1;
        var m=sM?+sM.value:0, b=sB?+sB.value:0;
        if(modo==='recta'){
          var paso=Math.max(1,Math.floor(N/45)), c=0;
          cx.strokeStyle='#fb7185'; cx.lineWidth=1.4;
          for(i=0;i<N;i+=paso){ if(!sel(i)) continue; cx.beginPath(); cx.moveTo(X(T[i]),Y(P[i])); cx.lineTo(X(T[i]),Y(m*T[i]+b)); cx.stroke(); c++; }
          cx.setLineDash([7,5]); cx.strokeStyle='#4ade80'; cx.lineWidth=2;
          cx.beginPath(); cx.moveTo(X(tmin),Y(mo*tmin+bo)); cx.lineTo(X(tmax),Y(mo*tmax+bo)); cx.stroke(); cx.setLineDash([]);
          cx.fillStyle='#4ade80'; cx.textAlign='left'; cx.fillText('recta del programa',X(tmin)+6,Y(mo*tmin+bo)-8);
          cx.strokeStyle='#38bdf8'; cx.lineWidth=3;
          cx.beginPath(); cx.moveTo(X(x0),Y(m*x0+b)); cx.lineTo(X(x1),Y(m*x1+b)); cx.stroke();
        } else if(chkRec && chkRec.checked){
          cx.strokeStyle='#4ade80'; cx.lineWidth=3;
          cx.beginPath(); cx.moveTo(X(tmin),Y(mo*tmin+bo)); cx.lineTo(X(tmax),Y(mo*tmax+bo)); cx.stroke();
        }
      }
      function refresca(){
        if(modo==='recta'){
          var m=+sM.value, b;
          if(chkPiv && chkPiv.checked){ b=ym-m*xm; sB.value=b.toFixed(1); } else b=+sB.value;
          sB.disabled=!!(chkPiv && chkPiv.checked);
          vM.textContent=fmt(m,2); vB.textContent=fmt(b,1);
          var c=calc(m,b), o=calc(mo,bo);
          $('.k-sse',box).textContent=fmt(c.sse,0); $('.k-rmse',box).textContent=fmt(c.rmse,2)+' MW';
          $('.k-mae',box).textContent=fmt(c.mae,2)+' MW'; $('.k-r2',box).textContent=fmt(c.r2,3);
          $('.k-eq',box).textContent='Potencia = '+fmt(m,2)+' · T '+(b<0?'− ':'+ ')+fmt(Math.abs(b),1);
          var ratio=c.sse/o.sse, pct=Math.max(4,Math.min(100,100/ratio));
          var bar=$('.labr-barra i',box); bar.style.width=pct+'%'; bar.style.background=ratio<1.02?'#4ade80':(ratio<2?'#fbbf24':'#fb7185');
          $('.k-ratio',box).textContent='Tu error es ×'+fmt(ratio,2)+' el de la recta del programa';
          var cerca=Math.abs(m-mo)<0.03 && Math.abs(b-bo)<0.8;
          msg.textContent= cerca ? '🏆 ¡Has encontrado la recta de mínimos cuadrados! Coincide con la del programa.' :
            (ratio>5 ? 'Muy lejos. Los segmentos rojos son los errores: busca que sean lo más cortos posibles. Pista: la pendiente debería ser negativa (más calor, menos potencia).' :
             'Cada segmento rojo es un error (residuo). El SSE suma todos al cuadrado. Intenta bajar la barra hasta que llegue al 100 %.');
        } else {
          var cu=calc(mo,bo);
          $('.k-n',box).textContent=fmt(cu.n,0);
          $('.k-cor',box).textContent=fmt(cor,3);
          $('.k-rt',box).textContent=fmt(tmin,1)+' a '+fmt(tmax,1)+' °C';
          $('.k-rp',box).textContent=fmt(pmin,0)+' a '+fmt(pmax,0)+' MW';
        }
        dibuja();
      }
      [sM,sB,selG,chkPiv,chkRec].forEach(function(el){ if(el){ el.addEventListener('input',refresca); el.addEventListener('change',refresca); } });
      var bs=$('.b-sol',box); if(bs) bs.addEventListener('click',function(){ if(chkPiv) chkPiv.checked=false; sM.value=mo.toFixed(2); sB.value=bo.toFixed(1); refresca(); });
      var b0=$('.b-cero',box); if(b0) b0.addEventListener('click',function(){ sM.value=0; sB.value=ym.toFixed(1); if(chkPiv) chkPiv.checked=false; refresca(); });
      window.addEventListener('resize',dibuja);
      refresca();
    }, function(){
      cuerpo.innerHTML='<div class="labr-falta">Todavía no están los datos reales de este gráfico. Ejecuta el cuaderno de Colab y sube el archivo <b>datos--'+(box.getAttribute('data-id')||'')+'.json</b> a la raíz del repositorio.</div>';
    });
  }
  $$('.labr').forEach(iniciaLab);
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
