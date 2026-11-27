
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
  var META_DEF={"xl": "Temperatura ambiente (°C)", "yl": "Potencia (MW)", "xu": "°C", "yu": "MW", "xn": "Temperatura", "yn": "Potencia", "xv": "T", "md": 2, "bd": 1, "bst": 0.1, "mstep": 0.01, "mspan": 3, "bspan": 120, "xd": 1, "yd": 0, "yp": 1, "pista": "la pendiente debería ser negativa (más calor, menos potencia)", "bx": [0, 45], "by": [380, 520], "ax": [0, 40], "ay": [400, 505], "ax1": 15, "frase_dentro": "A {x} {xu} esperamos {h} {yu}; el 95 % de las veces el valor real quedará entre {lo} y {hi} {yu}.", "frase_fuera": "⚠ A {x} {xu} no hay datos reales (solo de {tmin} a {tmax} {xu}). La recta da {h} {yu}, pero es una extrapolación: no te fíes.", "frase_sube": "Si x sube {d} {xu}, el valor estimado cambia {c} {yu} (pendiente × {d}).", "tol": [1, 15, 1, 5], "xs": [0, 45, 0.5, 25], "dmax": [1, 10, 1, 5]};
  function metaDe(D){ var d={}, k, M=D.meta||{}; for(k in META_DEF){ d[k]=META_DEF[k]; } for(k in M){ d[k]=M[k]; } return d; }
  function plantilla(t,v){ var k; for(k in v){ t=t.split('{'+k+'}').join(v[k]); } return t; }
  var cacheDatos={};
  function cargaDatos(src){
    if(!cacheDatos[src]) cacheDatos[src]=new Promise(function(ok,fail){
      function porScript(){
        var js=src.replace(/[.]json$/,'.js'), s=document.createElement('script'), id=src.split('/').pop().replace(/[.]json$/,'');
        s.onload=function(){ if(window.MMD&&window.MMD[id]) ok(window.MMD[id]); else fail(new Error('no')); };
        s.onerror=function(){ fail(new Error('no')); };
        s.src=js; document.head.appendChild(s);
      }
      if(location.protocol==='file:'){ porScript(); return; }
      fetch(src).then(function(r){ if(!r.ok) throw new Error('no'); return r.json(); }).then(ok,porScript);
    });
    return cacheDatos[src];
  }
  function iniciaLab(box){
    var src=box.getAttribute('data-src'), modo=box.getAttribute('data-modo')||'recta';
    var cuerpo=$('.labr-cuerpo',box);
    cargaDatos(src).then(function(D){
      var M=metaDe(D);
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
        sM.min=(mo-M.mspan).toFixed(4); sM.max=(mo+M.mspan).toFixed(4); sM.step=String(M.mstep);
        sB.min=(bo-M.bspan).toFixed(3); sB.max=(bo+M.bspan).toFixed(3); sB.step=String(M.bst);
        sM.value=0; sB.value=ym.toFixed(M.bd);
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
        var gx=(tmax-tmin)*0.03, gy=(pmax-pmin)*0.08, x0=tmin-gx,x1=tmax+gx,y0=pmin-gy,y1=pmax+gy;
        var X=function(x){ return L+(x-x0)*(W-L-Rr)/(x1-x0); }, Y=function(y){ return H-Bb-(y-y0)*(H-Tt-Bb)/(y1-y0); };
        cx.clearRect(0,0,W,H);
        cx.font='11px sans-serif'; cx.fillStyle='#8896ad'; cx.strokeStyle='#1d2b44'; cx.lineWidth=1;
        var k,v;
        for(k=0;k<=5;k++){ v=y0+(y1-y0)*k/5; cx.beginPath(); cx.moveTo(L,Y(v)); cx.lineTo(W-Rr,Y(v)); cx.stroke(); cx.textAlign='right'; cx.fillText(v.toFixed((y1-y0)<30?1:0),L-6,Y(v)+4); }
        for(k=0;k<=6;k++){ v=x0+(x1-x0)*k/6; cx.textAlign='center'; cx.fillText(Math.round(v),X(v),H-Bb+16); }
        cx.fillStyle='#cbd5e1'; cx.textAlign='center'; cx.fillText(M.xl,(L+W-Rr)/2,H-6);
        cx.save(); cx.translate(13,(Tt+H-Bb)/2); cx.rotate(-Math.PI/2); cx.fillText(M.yl,0,0); cx.restore();
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
      function dibujaRes(){
        var W=cv.clientWidth, H=Math.round(W*0.5), dpr=window.devicePixelRatio||1;
        cv.width=W*dpr; cv.height=H*dpr; cv.style.height=H+'px'; cx.setTransform(dpr,0,0,dpr,0,0);
        var xs=[],rs=[],i,n=0,sr=0,sq=0,mx=0;
        for(i=0;i<N;i++){ if(!sel(i)) continue; var pr=mo*T[i]+bo, r=P[i]-pr; xs.push(pr); rs.push(r); n++; sr+=r; sq+=r*r; if(Math.abs(r)>mx) mx=Math.abs(r); }
        var media=sr/n, sd=Math.sqrt(sq/n-media*media);
        var rgx=Math.max.apply(null,xs)-Math.min.apply(null,xs), xa=Math.min.apply(null,xs)-rgx*0.05, xb=Math.max.apply(null,xs)+rgx*0.05, st=mx>40?10:(mx>16?5:(mx>7?2:(mx>3?1:0.5))), ya=-Math.ceil(mx/st)*st-st*0.4, yb=Math.ceil(mx/st)*st+st*0.4;
        var L=54,Rr=12,Tt=12,Bb=40;
        var X=function(x){ return L+(x-xa)*(W-L-Rr)/(xb-xa); }, Y=function(y){ return H-Bb-(y-ya)*(H-Tt-Bb)/(yb-ya); };
        cx.clearRect(0,0,W,H); cx.font='11px sans-serif'; cx.strokeStyle='#1d2b44'; cx.lineWidth=1; cx.fillStyle='#8896ad';
        var k,v;
        for(k=-8;k<=8;k++){ v=k*st; if(v<ya||v>yb) continue; cx.beginPath(); cx.moveTo(L,Y(v)); cx.lineTo(W-Rr,Y(v)); cx.stroke(); cx.textAlign='right'; cx.fillText(+v.toFixed(1),L-6,Y(v)+4); }
        for(k=0;k<=6;k++){ v=xa+(xb-xa)*k/6; cx.textAlign='center'; cx.fillText(Math.round(v),X(v),H-Bb+16); }
        cx.fillStyle='#cbd5e1'; cx.textAlign='center'; cx.fillText(M.yn+' predicha ('+M.yu+')',(L+W-Rr)/2,H-6);
        cx.save(); cx.translate(13,(Tt+H-Bb)/2); cx.rotate(-Math.PI/2); cx.fillText('Residuo = real − predicho ('+M.yu+')',0,0); cx.restore();
        cx.globalAlpha=0.3; cx.fillStyle='#38bdf8';
        for(i=0;i<xs.length;i++){ cx.beginPath(); cx.arc(X(xs[i]),Y(rs[i]),2,0,6.2832); cx.fill(); }
        cx.globalAlpha=1; cx.lineWidth=1.4; cx.setLineDash([5,4]); cx.strokeStyle='#fbbf24';
        [1.96*sd,-1.96*sd].forEach(function(y){ cx.beginPath(); cx.moveTo(L,Y(y)); cx.lineTo(W-Rr,Y(y)); cx.stroke(); });
        cx.fillStyle='#fbbf24'; cx.textAlign='left'; cx.fillText('±1,96·σ (≈95 % de los errores)',L+6,Y(1.96*sd)-5);
        cx.strokeStyle='#fb7185'; cx.lineWidth=2; cx.beginPath(); cx.moveTo(L,Y(0)); cx.lineTo(W-Rr,Y(0)); cx.stroke(); cx.setLineDash([]);
        cx.fillStyle='#fb7185'; cx.fillText('error cero',L+6,Y(0)-5);
        $('.k-n',box).textContent=fmt(n,0); $('.k-rm',box).textContent=fmt(media,2)+' '+M.yu;
        $('.k-rs',box).textContent=fmt(sd,2)+' '+M.yu; $('.k-rx',box).textContent=fmt(mx,1)+' '+M.yu;
      }
      function pinta(){ if(modo==='residuos') dibujaRes(); else dibuja(); }
      function refresca(){
        if(modo==='recta'){
          var m=+sM.value, b;
          if(chkPiv && chkPiv.checked){ b=ym-m*xm; sB.value=b.toFixed(M.bd+1); } else b=+sB.value;
          sB.disabled=!!(chkPiv && chkPiv.checked);
          vM.textContent=fmt(m,M.md); vB.textContent=fmt(b,M.bd);
          var c=calc(m,b), o=calc(mo,bo);
          $('.k-sse',box).textContent=fmt(c.sse,0); $('.k-rmse',box).textContent=fmt(c.rmse,2)+' '+M.yu;
          $('.k-mae',box).textContent=fmt(c.mae,2)+' '+M.yu; $('.k-r2',box).textContent=fmt(c.r2,3);
          $('.k-eq',box).textContent=M.yn+' = '+fmt(m,M.md)+' · '+M.xv+' '+(b<0?'− ':'+ ')+fmt(Math.abs(b),M.bd);
          var ratio=c.sse/o.sse, pct=Math.max(4,Math.min(100,100/ratio));
          var bar=$('.labr-barra i',box); bar.style.width=pct+'%'; bar.style.background=ratio<1.02?'#4ade80':(ratio<2?'#fbbf24':'#fb7185');
          $('.k-ratio',box).textContent='Tu error es ×'+fmt(ratio,2)+' el de la recta del programa';
          var cerca=Math.abs(m-mo)<M.mspan*0.01 && Math.abs(b-bo)<M.bspan*0.0067;
          msg.textContent= cerca ? '🏆 ¡Has encontrado la recta de mínimos cuadrados! Coincide con la del programa.' :
            (ratio>5 ? 'Muy lejos. Los segmentos rojos son los errores: busca que sean lo más cortos posibles. Pista: '+M.pista+'.' :
             'Cada segmento rojo es un error (residuo). El SSE suma todos al cuadrado. Intenta bajar la barra hasta que llegue al 100 %.');
        } else if(modo==='nube'){
          var cu=calc(mo,bo);
          $('.k-n',box).textContent=fmt(cu.n,0);
          $('.k-cor',box).textContent=fmt(cor,3);
          $('.k-rt',box).textContent=fmt(tmin,M.xd)+' a '+fmt(tmax,M.xd)+' '+M.xu;
          $('.k-rp',box).textContent=fmt(pmin,M.yd)+' a '+fmt(pmax,M.yd)+' '+M.yu;
        }
        pinta();
      }
      [sM,sB,selG,chkPiv,chkRec].forEach(function(el){ if(el){ el.addEventListener('input',refresca); el.addEventListener('change',refresca); } });
      var bs=$('.b-sol',box); if(bs) bs.addEventListener('click',function(){ if(chkPiv) chkPiv.checked=false; sM.value=mo.toFixed(M.md+2); sB.value=bo.toFixed(M.bd+1); refresca(); });
      var b0=$('.b-cero',box); if(b0) b0.addEventListener('click',function(){ sM.value=0; sB.value=ym.toFixed(M.bd); if(chkPiv) chkPiv.checked=false; refresca(); });
      window.addEventListener('resize',pinta);
      refresca();
    }, function(){
      cuerpo.innerHTML='<div class="labr-falta">Todavía no están los datos reales de este gráfico. Ejecuta el cuaderno de Colab y sube el archivo <b>datos--'+(box.getAttribute('data-id')||'')+'.json</b> a la raíz del repositorio.</div>';
    });
  }
  $$('.labr:not(.grx)').forEach(iniciaLab);
  /* ---- gráficos explicados con los datos reales (histograma, real vs predicho, banda, reparto, anatomía) ---- */
  function iniciaGraf(box){
    var modo=box.getAttribute('data-modo'), cuerpo=$('.labr-cuerpo',box);
    cargaDatos(box.getAttribute('data-src')).then(function(D){
      var M=metaDe(D);
      var N=D.t.length, T=D.t, P=D.p, E=D.e, mo=D.m, bo=D.b, cv=$('canvas',box), cx=cv.getContext('2d'), i, k;
      var msg=$('.labr-msg',box), sl=$('.s1',box), sv=$('.v1',box), selG=$('select',box);
      var tmin=Math.min.apply(null,T), tmax=Math.max.apply(null,T), pmin=Math.min.apply(null,P), pmax=Math.max.apply(null,P);
      function K(c,txt){ var e=$('.'+c,box); if(e) e.textContent=txt; }
      function lienzo(f){ var W=cv.clientWidth, H=Math.round(W*f), d=window.devicePixelRatio||1; cv.width=W*d; cv.height=H*d; cv.style.height=H+'px'; cx.setTransform(d,0,0,d,0,0); cx.clearRect(0,0,W,H); return {W:W,H:H}; }
      function ejes(L,x0,x1,y0,y1,xl,yl,dx){
        var W=L.W,H=L.H,l=54,r=12,t=12,b=40;
        var X=function(x){ return l+(x-x0)*(W-l-r)/(x1-x0); }, Y=function(y){ return H-b-(y-y0)*(H-t-b)/(y1-y0); };
        cx.font='11px sans-serif'; cx.strokeStyle='#1d2b44'; cx.lineWidth=1; cx.fillStyle='#8896ad'; cx.setLineDash([]);
        var v;
        for(k=0;k<=5;k++){ v=y0+(y1-y0)*k/5; cx.beginPath(); cx.moveTo(l,Y(v)); cx.lineTo(W-r,Y(v)); cx.stroke(); cx.textAlign='right'; cx.fillText((y1-y0)<30?v.toFixed(1):Math.round(v),l-6,Y(v)+4); }
        for(k=0;k<=6;k++){ v=x0+(x1-x0)*k/6; cx.textAlign='center'; cx.fillText(dx?v.toFixed(dx):Math.round(v),X(v),H-b+16); }
        cx.fillStyle='#cbd5e1'; cx.textAlign='center'; cx.fillText(xl,(l+W-r)/2,H-6);
        cx.save(); cx.translate(13,(t+H-b)/2); cx.rotate(-Math.PI/2); cx.fillText(yl,0,0); cx.restore();
        return {X:X,Y:Y,l:l,r:r,t:t,b:b,W:W,H:H};
      }
      function rotulo(txt,x,y,col,al){ cx.fillStyle=col; cx.textAlign=al||'left'; cx.font='12px sans-serif'; cx.fillText(txt,x,y); cx.font='11px sans-serif'; }
      var pinta=function(){};

      if(modo==='hist'){
        var vr=box.getAttribute('data-var'), vals=[], etx;
        if(vr==='t'){ vals=T.slice(); etx=M.xl; }
        else if(vr==='p'){ vals=P.slice(); etx=M.yl; }
        else { for(i=0;i<N;i++){ if(E[i]) vals.push(P[i]-(mo*T[i]+bo)); } etx='Residuo = real − predicho ('+M.yu+')'; }
        var n=vals.length, so=vals.slice().sort(function(a,b){ return a-b; }), mn=so[0], mx=so[n-1], me=0, sd=0;
        vals.forEach(function(v){ me+=v; }); me/=n; vals.forEach(function(v){ sd+=(v-me)*(v-me); }); sd=Math.sqrt(sd/n);
        var med=(n%2)?so[(n-1)/2]:(so[n/2-1]+so[n/2])/2, dec=(mx-mn)>60?0:((mx-mn)>6?1:2);
        K('k-n',fmt(n,0)); K('k-me',fmt(me,vr==='r'?2:2)); K('k-md',fmt(med,2)); K('k-sd',fmt(sd,2)); K('k-mn',fmt(mn,2)); K('k-mx',fmt(mx,2));
        pinta=function(){
          var nb=+sl.value; sv.textContent=nb;
          var L=lienzo(0.55), w=(mx-mn)/nb, cnt=[]; for(k=0;k<nb;k++) cnt.push(0);
          vals.forEach(function(v){ cnt[Math.min(nb-1,Math.floor((v-mn)/w))]++; });
          var cm=Math.max.apply(null,cnt), top=Math.ceil(cm/50)*50;
          var a=ejes(L,mn,mx,0,top,etx,'nº de registros',dec);
          cx.fillStyle='rgba(56,189,248,.38)'; cx.strokeStyle='#38bdf8'; cx.lineWidth=1;
          for(k=0;k<nb;k++){ var xa=a.X(mn+k*w), xb=a.X(mn+(k+1)*w), y=a.Y(cnt[k]); cx.fillRect(xa+1,y,xb-xa-2,a.Y(0)-y); cx.strokeRect(xa+1,y,xb-xa-2,a.Y(0)-y); }
          cx.lineWidth=2; cx.setLineDash([6,4]);
          cx.strokeStyle='#fbbf24'; cx.beginPath(); cx.moveTo(a.X(me),a.t); cx.lineTo(a.X(me),a.Y(0)); cx.stroke();
          cx.strokeStyle='#4ade80'; cx.beginPath(); cx.moveTo(a.X(med),a.t); cx.lineTo(a.X(med),a.Y(0)); cx.stroke(); cx.setLineDash([]);
          rotulo('media '+fmt(me,2),a.X(me)+(me>=med?6:-6),a.t+12,'#fbbf24',me>=med?'left':'right');
          rotulo('mediana '+fmt(med,2),a.X(med)+(me>=med?-6:6),a.t+28,'#4ade80',me>=med?'right':'left');
          msg.textContent='Con '+nb+' barras, la más alta reúne '+fmt(cm,0)+' registros ('+fmt(100*cm/n,1)+' % del total).';
        };
        sl.addEventListener('input',pinta);
      }

      else if(modo==='reparto'){
        var tt=0; for(i=0;i<N;i++) tt+=E[i];
        K('k-tr',fmt(N-tt,0)+' ('+fmt(100*(N-tt)/N,0)+' %)'); K('k-te',fmt(tt,0)+' ('+fmt(100*tt/N,0)+' %)');
        pinta=function(){
          var L=lienzo(0.46), cols=25, rows=8, W=L.W, H=L.H, pad=10, gap=3, cw=(W-2*pad-(cols-1)*gap)/cols, ch=Math.min(cw,(H-60-(rows-1)*gap)/rows);
          for(k=0;k<cols*rows;k++){
            var idx=Math.floor(k*N/(cols*rows)), c=k%cols, r=Math.floor(k/cols);
            cx.fillStyle=E[idx]?'#fbbf24':'#38bdf8'; cx.globalAlpha=.85;
            cx.fillRect(pad+c*(cw+gap),pad+r*(ch+gap),cw,ch);
          }
          cx.globalAlpha=1;
          var yb=pad+rows*(ch+gap)+14, wb=W-2*pad, w1=wb*(N-tt)/N;
          cx.fillStyle='#38bdf8'; cx.fillRect(pad,yb,w1,18); cx.fillStyle='#fbbf24'; cx.fillRect(pad+w1,yb,wb-w1,18);
          cx.fillStyle='#04121f'; cx.font='bold 12px sans-serif'; cx.textAlign='center';
          cx.fillText('Entrenamiento 80 %',pad+w1/2,yb+13); cx.fillText('Prueba 20 %',pad+w1+(wb-w1)/2,yb+13); cx.font='11px sans-serif';
          msg.textContent='Cada cuadradito es una muestra de 200 registros elegidos a lo largo de toda la tabla: los de prueba (ámbar) quedan mezclados al azar entre los de entrenamiento (azul).';
        };
      }

      else if(modo==='realpred'){
        pinta=function(){
          var g=selG.value, tol=+sl.value; sv.textContent=tol;
          var xs=[], ys=[], n=0, sse=0, sae=0, sp=0, dentro=0, pr, e;
          for(i=0;i<N;i++){ if((g==='train'&&E[i])||(g==='test'&&!E[i])) continue;
            pr=mo*T[i]+bo; e=P[i]-pr; xs.push(pr); ys.push(P[i]); n++; sse+=e*e; sae+=Math.abs(e); sp+=P[i]; if(Math.abs(e)<=tol) dentro++; }
          var pm=sp/n, sst=0; ys.forEach(function(y){ sst+=(y-pm)*(y-pm); });
          var gp=(pmax-pmin)*0.1, lo=pmin-gp, hi=pmax+gp, L=lienzo(0.66), a=ejes(L,lo,hi,lo,hi,M.yn+' predicha por la recta ('+M.yu+')',M.yn+' real medida ('+M.yu+')',(hi-lo)<30?1:0);
          for(i=0;i<xs.length;i++){ var ok=Math.abs(ys[i]-xs[i])<=tol; cx.globalAlpha=ok?0.25:0.7; cx.fillStyle=ok?'#38bdf8':'#fb7185';
            cx.beginPath(); cx.arc(a.X(xs[i]),a.Y(ys[i]),1.9,0,6.2832); cx.fill(); }
          cx.globalAlpha=1; cx.setLineDash([5,4]); cx.lineWidth=1.3; cx.strokeStyle='#fbbf24';
          [tol,-tol].forEach(function(d){ cx.beginPath(); cx.moveTo(a.X(lo),a.Y(lo+d)); cx.lineTo(a.X(hi),a.Y(hi+d)); cx.stroke(); });
          cx.setLineDash([8,5]); cx.lineWidth=2.4; cx.strokeStyle='#4ade80'; cx.beginPath(); cx.moveTo(a.X(lo),a.Y(lo)); cx.lineTo(a.X(hi),a.Y(hi)); cx.stroke(); cx.setLineDash([]);
          rotulo('predicción perfecta (real = predicho)',a.X(lo)+8,a.Y(lo+(hi-lo)*0.2)-4,'#4ade80');
          rotulo('rojo: error mayor que ±'+tol+' '+M.yu,a.X(hi)-8,a.Y(lo)-12,'#fb7185','right');
          K('k-r2',fmt(1-sse/sst,4)); K('k-rmse',fmt(Math.sqrt(sse/n),3)+' '+M.yu); K('k-mae',fmt(sae/n,3)+' '+M.yu); K('k-in',fmt(100*dentro/n,1)+' %');
          msg.textContent='El '+fmt(100*dentro/n,1)+' % de las predicciones queda a menos de '+tol+' '+M.yu+' del valor real.';
        };
        sl.addEventListener('input',pinta); selG.addEventListener('change',pinta);
      }

      else if(modo==='banda'){
        var tn=0, xb0=0, sx=0, sse0=0;
        for(i=0;i<N;i++){ if(!E[i]){ tn++; xb0+=T[i]; } } xb0/=tn;
        for(i=0;i<N;i++){ if(!E[i]){ sx+=(T[i]-xb0)*(T[i]-xb0); var rr=P[i]-(mo*T[i]+bo); sse0+=rr*rr; } }
        var s0=Math.sqrt(sse0/(tn-2));
        var t0=box.getAttribute('data-t'); if(t0) sl.value=t0;
        var inter=function(x){ var h=mo*x+bo, mg=1.9603*s0*Math.sqrt(1+1/tn+(x-xb0)*(x-xb0)/sx); return {h:h,lo:h-mg,hi:h+mg,mg:mg}; };
        pinta=function(){
          var x=+sl.value; sv.textContent=fmt(x,M.xd>0?1:0);
          var L=lienzo(0.62), xa=M.bx[0], xz=M.bx[1], ya=M.by[0], yz=M.by[1], NS=60, a=ejes(L,xa,xz,ya,yz,M.xl,M.yl);
          cx.fillStyle='rgba(251,113,133,.10)';
          cx.fillRect(a.X(xa),a.t,a.X(tmin)-a.X(xa),a.Y(ya)-a.t); cx.fillRect(a.X(tmax),a.t,a.X(xz)-a.X(tmax),a.Y(ya)-a.t);
          rotulo('sin datos',a.X(xa)+6,a.t+14,'#fb7185'); rotulo('sin datos',a.X(xz)-6,a.t+14,'#fb7185','right');
          cx.globalAlpha=.16; cx.fillStyle='#38bdf8';
          for(i=0;i<N;i++){ if(E[i]) continue; cx.beginPath(); cx.arc(a.X(T[i]),a.Y(P[i]),1.7,0,6.2832); cx.fill(); }
          cx.globalAlpha=1; cx.beginPath();
          for(k=0;k<=NS;k++){ var xk=xa+(xz-xa)*k/NS, q=inter(xk); if(k===0) cx.moveTo(a.X(xk),a.Y(q.hi)); else cx.lineTo(a.X(xk),a.Y(q.hi)); }
          for(k=NS;k>=0;k--){ var xj=xa+(xz-xa)*k/NS; cx.lineTo(a.X(xj),a.Y(inter(xj).lo)); }
          cx.closePath(); cx.fillStyle='rgba(74,222,128,.17)'; cx.fill(); cx.setLineDash([5,4]); cx.strokeStyle='#4ade80'; cx.lineWidth=1.3; cx.stroke(); cx.setLineDash([]);
          cx.strokeStyle='#38bdf8'; cx.lineWidth=2.6; cx.beginPath(); cx.moveTo(a.X(xa),a.Y(mo*xa+bo)); cx.lineTo(a.X(xz),a.Y(mo*xz+bo)); cx.stroke();
          var q2=inter(x);
          cx.strokeStyle='rgba(230,237,247,.55)'; cx.setLineDash([3,4]); cx.lineWidth=1; cx.beginPath(); cx.moveTo(a.X(x),a.t); cx.lineTo(a.X(x),a.Y(ya)); cx.stroke(); cx.setLineDash([]);
          cx.strokeStyle='#fbbf24'; cx.lineWidth=5; cx.lineCap='round'; cx.beginPath(); cx.moveTo(a.X(x),a.Y(q2.lo)); cx.lineTo(a.X(x),a.Y(q2.hi)); cx.stroke(); cx.lineCap='butt';
          cx.fillStyle='#fff'; cx.strokeStyle='#04121f'; cx.lineWidth=2; cx.beginPath(); cx.arc(a.X(x),a.Y(q2.h),6,0,6.2832); cx.fill(); cx.stroke();
          var dentro=(x>=tmin&&x<=tmax);
          K('k-h',fmt(q2.h,M.yp)+' '+M.yu); K('k-lo',fmt(q2.lo,M.yp)+' '+M.yu); K('k-hi',fmt(q2.hi,M.yp)+' '+M.yu); K('k-es',dentro?'Dentro ✓':'Fuera ⚠');
          var es=$('.k-es',box); if(es) es.style.color=dentro?'#4ade80':'#fb7185';
          var vv={x:fmt(x,M.xd),xu:M.xu,yu:M.yu,h:fmt(q2.h,M.yp),lo:fmt(q2.lo,M.yp),hi:fmt(q2.hi,M.yp),tmin:fmt(tmin,M.xd),tmax:fmt(tmax,M.xd)};
          msg.textContent=dentro?plantilla(M.frase_dentro,vv):plantilla(M.frase_fuera,vv);
        };
        sl.addEventListener('input',pinta);
      }

      else if(modo==='anatomia'){
        K('k-m',fmt(mo,M.md+2)+' '+M.yu+'/'+M.xu); K('k-b',fmt(bo,M.bd+1)+' '+M.yu);
        pinta=function(){
          var d=+sl.value; sv.textContent=d;
          var L=lienzo(0.62), a=ejes(L,M.ax[0],M.ax[1],M.ay[0],M.ay[1],M.xl,M.yl);
          cx.globalAlpha=.16; cx.fillStyle='#38bdf8';
          for(i=0;i<N;i++){ cx.beginPath(); cx.arc(a.X(T[i]),a.Y(P[i]),1.7,0,6.2832); cx.fill(); }
          cx.globalAlpha=1; cx.strokeStyle='#38bdf8'; cx.lineWidth=3; cx.beginPath(); cx.moveTo(a.X(M.ax[0]),a.Y(mo*M.ax[0]+bo)); cx.lineTo(a.X(M.ax[1]),a.Y(mo*M.ax[1]+bo)); cx.stroke();
          cx.fillStyle='#fb7185'; cx.beginPath(); cx.arc(a.X(0),a.Y(bo),6,0,6.2832); cx.fill();
          rotulo('b = '+fmt(bo,M.bd)+' '+M.yu+'  (la recta, cuando x = 0)',a.X(0)+10,a.Y(bo)-10,'#fb7185');
          var x1=M.ax1, y1=mo*x1+bo, x2=x1+d, y2=mo*x2+bo;
          cx.fillStyle='rgba(251,191,36,.18)'; cx.strokeStyle='#fbbf24'; cx.lineWidth=2; cx.setLineDash([5,4]);
          cx.beginPath(); cx.moveTo(a.X(x1),a.Y(y1)); cx.lineTo(a.X(x2),a.Y(y1)); cx.lineTo(a.X(x2),a.Y(y2)); cx.closePath(); cx.fill(); cx.stroke(); cx.setLineDash([]);
          rotulo('+'+d+' '+M.xu,(a.X(x1)+a.X(x2))/2,a.Y(y1)-8,'#fbbf24','center');
          rotulo(fmt(mo*d,M.yp)+' '+M.yu,a.X(x2)+8,(a.Y(y1)+a.Y(y2))/2+4,'#fbbf24');
          K('k-d',fmt(mo*d,M.yp+1)+' '+M.yu);
          msg.textContent=plantilla(M.frase_sube,{d:d,xu:M.xu,yu:M.yu,c:fmt(mo*d,M.yp+1)});
        };
        sl.addEventListener('input',pinta);
      }

      window.addEventListener('resize',pinta);
      pinta();
    }, function(){
      cuerpo.innerHTML='<div class="labr-falta">Todavía no están los datos reales de este gráfico. Sube el archivo <b>datos--'+(box.getAttribute('data-id')||'')+'.json</b> a la raíz del repositorio.</div>';
    });
  }
  $$('.grx').forEach(iniciaGraf);

  (function(){
    function lee(k){ try{ return localStorage.getItem(k); }catch(e){ return null; } }
    function pinta(){
      $$('.red[data-red]').forEach(function(r){
        var pid=r.getAttribute('data-red'), prev=true;
        $$('.rn',r).forEach(function(g){
          var i=g.getAttribute('data-i'), ok=lee('mm-ok:'+pid+':'+i)==='1', c=g.querySelector('circle');
          c.setAttribute('fill', ok?'#14532d':'#16213a'); c.setAttribute('stroke', ok?'#4ade80':(prev?'#38bdf8':'#22304a'));
          prev=ok;
          var ln=r.querySelector('.rl[data-i="'+(parseInt(i,10)-1)+'"]');
          if(ln){ ln.setAttribute('stroke', ok?'#38bdf8':'#22304a'); ln.setAttribute('stroke-width', ok?'2.4':'1.6'); }
        });
      });
    }
    pinta(); document.addEventListener('click',function(){ setTimeout(pinta,50); }); window.addEventListener('storage',pinta);
  })();

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
