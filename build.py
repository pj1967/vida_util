#!/usr/bin/env python3
"""
Mente Máquina — generador de la web.

Cada vez que se ejecuta:
  1. Lee los feeds RSS de feeds.json y se queda solo con lo relevante
     (inteligencia artificial, robótica, automatización) según las listas de palabras.
  2. Clasifica cada noticia por tema y la guarda en data/articulos.json (sin duplicados).
  3. Lee los resúmenes semanales de data/resumenes/*.json (si los hay).
  4. Regenera la web completa en docs/.

Solo se guardan título, fuente, fecha y enlace a la noticia original.
Uso:  python build.py                  (descarga + genera)
      python build.py --sin-descarga   (solo regenera la web con lo ya guardado)
"""
import argparse
import hashlib
import html
import json
import os
import unicodedata
import re
import shutil
import socket
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

try:
    from zoneinfo import ZoneInfo
    ZONA = ZoneInfo("Europe/Madrid")
except Exception:  # pragma: no cover
    ZONA = timezone.utc

RAIZ = Path(__file__).resolve().parent
USER_AGENT = "MenteMaquina/1.0 (+lector RSS personal)"
MAX_POR_FEED_DEFECTO = 10
RESUMEN_MAX = 500  # caracteres del extracto del feed, solo para decidir relevancia y tema

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago",
                "sep", "oct", "nov", "dic"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

COLORES = {
    "ia": "#818cf8",
    "robotica": "#c084fc",
    "programacion": "#4ade80",
    "aeronautica": "#38bdf8",
    "otros": "#fb7185",
}

# ----------------------------------------------------------------- estilo
CSS = """
:root{--fondo:#0b1220;--superficie:#111a2c;--superficie2:#16213a;--linea:#22304a;
 --tinta:#e6edf7;--suave:#9aa8bf;--acento:#38bdf8}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;scroll-behavior:smooth;background:var(--fondo)}
body{margin:0;background:var(--fondo);color:var(--tinta);
 font:16px/1.55 Inter,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--acento);text-decoration:none}
a:hover{text-decoration:underline}
.contenedor{max-width:1080px;margin:0 auto;padding:0 18px}
header.sitio{padding:30px 0 22px;
 background:radial-gradient(900px 320px at 12% -30%,rgba(56,189,248,.20),transparent 65%),
            radial-gradient(700px 260px at 90% -40%,rgba(129,140,248,.16),transparent 65%)}
.hero{display:flex;align-items:center;gap:18px}
.logo{flex:none;display:block;line-height:0;transition:transform .2s ease}
.logo:hover{transform:translateY(-2px) scale(1.04)}
.logo svg{width:84px;height:84px;overflow:visible}
.hero h1{margin:0;font-size:2.4rem;line-height:1.05;font-weight:800;letter-spacing:-.025em}
.hero h1 a{color:var(--tinta);text-decoration:none}
.hero h1 span{color:var(--acento)}
.lema{margin:6px 0 0;font-size:1.15rem;font-weight:700;display:inline-block;
 background:linear-gradient(90deg,#38bdf8,#818cf8);-webkit-background-clip:text;background-clip:text;color:transparent}
.subtitulo{margin:2px 0 0;color:var(--suave);font-size:.98rem}
.autor{margin:8px 0 0;color:var(--suave);font-size:.9rem}
.autor b,.pie .nombre{color:#f5c451;font-weight:700;letter-spacing:.01em}
.barra{position:sticky;top:0;z-index:50;background:rgba(11,18,32,.92);
 -webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);border-top:1px solid var(--linea);border-bottom:1px solid var(--linea)}
nav.menu{display:flex;flex-wrap:wrap;gap:8px;align-items:center;padding:10px 0}
nav.menu>a,.desplegable summary{display:inline-block;white-space:nowrap;padding:6px 14px;border:1px solid var(--linea);
 border-radius:999px;color:var(--tinta);font-size:.9rem;background:var(--superficie);cursor:pointer;list-style:none}
nav.menu>a:hover,.desplegable summary:hover{border-color:var(--acento);text-decoration:none}
nav.menu>a.activo,.desplegable.activo summary{background:rgba(56,189,248,.14);border-color:var(--acento);
 color:var(--acento);font-weight:600}
.desplegable{position:relative}
.desplegable summary::-webkit-details-marker{display:none}
.desplegable summary::after{content:" \\25BE";font-size:.8em}
.panel{position:absolute;top:calc(100% + 8px);left:0;min-width:260px;display:flex;flex-direction:column;
 background:var(--superficie);border:1px solid var(--linea);border-radius:12px;padding:8px;
 box-shadow:0 14px 34px rgba(0,0,0,.55);z-index:60}
.panel a{display:flex;align-items:center;gap:10px;padding:9px 10px;border-radius:8px;color:var(--tinta)}
.panel a:hover{background:var(--superficie2);text-decoration:none}
main{padding:8px 0 48px}
.intro{margin:26px 0 16px;font-size:1.4rem;font-weight:700;letter-spacing:-.01em}
.intro small{display:block;margin-top:3px;font-size:.88rem;font-weight:400;color:var(--suave)}
.rejilla{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:18px}
.tema-card{position:relative;display:flex;flex-direction:column;gap:12px;background:var(--superficie);
 border:1px solid var(--linea);border-top:3px solid var(--c,var(--acento));border-radius:14px;
 padding:16px 18px 14px;transition:transform .15s ease,border-color .15s ease,box-shadow .15s ease}
.tema-card:hover{transform:translateY(-2px);border-color:var(--c,var(--acento));box-shadow:0 10px 28px rgba(0,0,0,.45)}
.enlace-tema{position:absolute;inset:0;z-index:1;border-radius:14px}
.tema-card header{display:flex;align-items:center;gap:10px}
.punto{display:inline-block;flex:none;width:10px;height:10px;border-radius:50%;background:var(--c,var(--acento));
 box-shadow:0 0 10px var(--c,var(--acento))}
.tema-card h2{margin:0;padding:0;border:0;flex:1;font-size:1.1rem;font-weight:700;color:var(--c,var(--acento))}
.cuenta{font-size:.78rem;color:var(--suave);white-space:nowrap}
.resumen{margin:0;color:var(--tinta);font-size:.96rem;line-height:1.62}
.nota{margin:0;color:var(--suave);font-size:.82rem;font-style:italic}
.fuentes{display:flex;flex-wrap:wrap;gap:6px;align-items:center;font-size:.78rem;color:var(--suave)}
.fuentes a{position:relative;z-index:2;padding:2px 10px;border:1px solid var(--linea);border-radius:999px;
 color:var(--tinta);background:var(--superficie2)}
.fuentes a:hover{border-color:var(--c,var(--acento));text-decoration:none}
.mas{margin-top:auto;padding-top:2px;font-size:.85rem;font-weight:600;color:var(--c,var(--acento))}
.tema-card li.item a{position:relative;z-index:2}
h2{font-size:1.25rem;line-height:1.3;font-weight:700;margin:30px 0 10px;padding-left:12px;
 border-left:4px solid var(--c,var(--acento))}
h2 small{font-size:.85rem;font-weight:400;color:var(--suave);margin-left:6px}
h3{font-size:1rem;margin:20px 0 4px;color:var(--suave);font-weight:600}
h3.semana{font-size:1.1rem;color:var(--tinta);margin:30px 0 10px;padding-top:14px;border-top:1px solid var(--linea)}
h4{margin:0 0 6px;font-size:1rem;color:var(--c,var(--acento))}
.desc{margin:0 0 6px;color:var(--suave)}
.bloque-resumen{background:var(--superficie);border:1px solid var(--linea);border-left:4px solid var(--c,var(--acento));
 border-radius:12px;padding:14px 16px;margin:12px 0}
.bloque-resumen p{margin:0 0 10px;line-height:1.62}
ul.lista{list-style:none;margin:0;padding:0}
li.item{padding:10px 0;border-bottom:1px solid var(--linea)}
li.item:last-child{border-bottom:0}
li.item a.titular{font-weight:600;color:var(--tinta);line-height:1.35}
li.item a.titular:hover{color:var(--acento)}
.meta{display:block;font-size:.8rem;color:var(--suave);margin-top:3px}
.nuevo{display:inline-block;margin-left:6px;padding:0 7px;border:1px solid var(--c,var(--acento));
 border-radius:8px;font-size:.68rem;color:var(--c,var(--acento));font-weight:600}
.etiqueta{color:var(--c,var(--acento));font-weight:600}
ul.flujo li.item{background:var(--superficie);border:1px solid var(--linea);border-left:3px solid var(--c,var(--acento));
 border-radius:10px;padding:11px 14px;margin:8px 0;transition:border-color .15s ease}
ul.flujo li.item:hover{border-color:var(--c,var(--acento))}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0 8px}
.chip-tema{font:inherit;font-size:.88rem;cursor:pointer;padding:6px 14px;border-radius:999px;
 border:1px solid var(--linea);background:var(--superficie);color:var(--tinta)}
.chip-tema:hover{border-color:var(--c,var(--acento))}
.chip-tema.activo{background:rgba(56,189,248,.14);border-color:var(--c,var(--acento));
 color:var(--c,var(--acento));font-weight:600}
.boton-mas{display:block;margin:18px auto 0;padding:10px 22px;font:inherit;font-weight:600;color:var(--acento);
 background:var(--superficie);border:1px solid var(--acento);border-radius:999px;cursor:pointer}
.boton-mas:hover{background:rgba(56,189,248,.12)}
.buscador{margin:16px 0 0}
.buscador input{width:100%;padding:11px 14px;font-size:1rem;color:var(--tinta);background:var(--superficie);
 border:1px solid var(--linea);border-radius:10px}
.buscador input::placeholder{color:var(--suave)}
.buscador input:focus{outline:2px solid rgba(56,189,248,.45);border-color:var(--acento)}
.tarjetas{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px;margin:14px 0}
.proyecto{display:flex;flex-direction:column;gap:8px;background:var(--superficie);border:1px solid var(--linea);
 border-radius:14px;padding:16px 18px}
.proyecto h3{margin:0;color:var(--tinta);font-size:1.05rem}
.proyecto p{margin:0;color:var(--suave);font-size:.93rem}
.proyecto a.ir{margin-top:auto;font-weight:600}
.estado{align-self:flex-start;font-size:.72rem;font-weight:700;padding:2px 10px;border-radius:999px;
 border:1px solid var(--acento);color:var(--acento)}
.estado.idea{border-color:var(--suave);color:var(--suave)}
.estado.curso{border-color:#fbbf24;color:#fbbf24}
.estado.publicado{border-color:#4ade80;color:#4ade80}
.fichas{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:10px;margin:12px 0}
.ficha{display:block;padding:12px 14px;border:1px solid var(--linea);border-left:4px solid var(--c,var(--acento));
 border-radius:10px;background:var(--superficie);color:var(--tinta)}
.ficha:hover{border-color:var(--c,var(--acento));text-decoration:none}
.ficha b{display:block}
.ficha span{color:var(--suave);font-size:.85rem}
.vacio{color:var(--suave);font-style:italic}
main p{max-width:70ch}
.bloque-resumen p,.resumen{max-width:none}
footer.pie{border-top:1px solid var(--linea);padding:18px 0 36px;color:var(--suave);font-size:.82rem}
.oculto{display:none!important}
.etiquetas{display:flex;flex-wrap:wrap;gap:6px}
.tag{font-size:.74rem;padding:2px 10px;border-radius:999px;border:1px solid var(--linea);color:var(--suave);background:var(--superficie2)}
.tag.nivel-basico{color:#4ade80;border-color:#2c6b46}
.tag.nivel-medio{color:#fbbf24;border-color:#7a5d17}
.tag.nivel-avanzado{color:#fb7185;border-color:#7d2f3d}
.tag.nivel-experto{color:#c084fc;border-color:#6b3d93}
.tag.area{color:var(--acento);border-color:#1d5b78}
.proyecto{border-top:3px solid var(--nv,var(--linea))}
.icono-card{font-size:1.5rem;line-height:1}
.pie-card{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:auto;padding-top:6px;border-top:1px dashed var(--linea)}
.pie-card a.ir{margin-top:0}
.tiempo{font-size:.8rem;font-weight:700;color:var(--nv,#38bdf8);background:var(--superficie2);border:1px solid var(--linea);border-radius:999px;padding:3px 10px;white-space:nowrap}
.intro-bloque{font-size:1.02rem;color:var(--tinta);margin:6px 0 14px;max-width:760px}
.stats-cab{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0 0;font-size:.82rem}
.stats-cab span{padding:3px 12px;border-radius:99px;border:1px solid var(--linea);background:var(--superficie2);color:var(--suave)}
.stats-cab b{color:#4ade80}
.esperado-g{margin:14px 0;padding:18px;border-radius:18px;border:1px solid #4ade8066;background:radial-gradient(500px 220px at 100% 0%,rgba(74,222,128,.12),transparent 70%),var(--superficie)}
.esperado-g h2{margin:0 0 4px}
.esperado-g svg{width:100%;height:auto;border-radius:12px;background:#0a1626;border:1px solid var(--linea);margin-top:8px}
.grafs-res{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px;margin:16px 0}
.grafs-res figure{margin:0;padding:14px;border-radius:16px;background:var(--superficie);border:1px solid var(--linea)}
.grafs-res h4{margin:0 0 6px;color:#4ade80}
.grafs-res img{width:100%;height:auto;border-radius:10px;background:#fff}
.fig-cuaderno{margin:10px 0;padding:12px;border-radius:16px;background:var(--superficie);border:1px solid var(--linea)}
.fig-cuaderno img{width:100%;height:auto;border-radius:10px;background:#fff;display:block}
.fig-cuaderno figcaption{margin-top:6px;font-size:.85rem;color:var(--suave)}
.sec-g{margin:18px 0 0;font-size:1.05rem;color:#4ade80}
.grafs-res svg{width:100%;height:auto;border-radius:10px;background:#0a1626;border:1px solid var(--linea)}
.grafs-res figcaption{margin-top:8px;font-size:.88rem;color:var(--suave)}
.kg{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-top:12px}
.kg div{padding:10px 12px;border-radius:12px;background:var(--superficie2);text-align:center}
.kg small{display:block;color:var(--suave);font-size:.72rem;text-transform:uppercase;letter-spacing:.08em}
.kg strong{font:800 1.3rem ui-monospace,monospace}
.concl{margin-top:12px;padding:12px 16px;border-radius:12px;border-left:4px solid #4ade80;background:rgba(74,222,128,.09)}
.btn-descarga{display:inline-block;padding:10px 18px;border-radius:999px;background:#4ade80;color:#04121f!important;font-weight:800;margin-right:12px}
.botones-pdf{margin:12px 0}
.btn-ayuda{display:flex;align-items:center;gap:12px;flex-wrap:wrap;background:var(--superficie);border:1px solid #4ade80;border-radius:14px;padding:12px 16px;margin:12px 0}
.btn-ayuda b{display:block}
.btn-ayuda a{margin-left:auto;font-weight:700;border:1px solid #4ade80;border-radius:999px;padding:6px 14px;white-space:nowrap}
.proyecto{position:relative;transition:transform .15s ease,border-color .15s ease,box-shadow .15s ease}
.proyecto:hover{transform:translateY(-2px);border-color:var(--acento);box-shadow:0 10px 28px rgba(0,0,0,.45)}
.proyecto a.ir::after{content:"";position:absolute;inset:0;border-radius:14px}
.destacado h2{margin-top:26px}
.bloque-proy{margin:22px 0 8px;padding:16px 16px 6px;background:rgba(255,255,255,.015);border:1px solid var(--linea);
 border-top:3px solid var(--c);border-radius:14px}
.bloque-proy>h3{display:flex;flex-wrap:wrap;align-items:baseline;gap:10px;margin:0 0 4px;font-size:1.2rem;color:var(--c)}
.bloque-proy>h3 small{font-weight:400;color:var(--suave);font-size:.85rem}
.subcols{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:10px 0}
.sub{display:flex;flex-direction:column;gap:12px}
.sub h4{margin:0;padding-bottom:4px;border-bottom:1px solid var(--linea);color:var(--suave);font-size:.82rem;
 text-transform:uppercase;letter-spacing:.06em}
.bloque-proy .tarjetas{margin:10px 0}
.cats{display:grid;grid-template-columns:repeat(auto-fit,minmax(225px,1fr));gap:18px;margin:14px 0}
.cats .tema-card{padding:20px 20px 16px;gap:10px}
.cats .tema-card h2{font-size:1.3rem}
.mini{margin:0;padding-left:18px;color:var(--suave);font-size:.88rem}
.mini li{margin:2px 0}
.ayuda{margin:8px 0 2px!important;padding:8px 12px;border-left:3px solid #38bdf8;background:rgba(56,189,248,.06);
 border-radius:0 8px 8px 0;font-size:.88rem!important;max-width:none}
.ayuda b{color:#38bdf8}
.ayuda a{white-space:normal}
.ayuda .sep{color:var(--suave);margin:0 6px}
.tabla-libro{width:100%;border-collapse:collapse;margin:10px 0;font-size:.92rem}
.tabla-libro th,.tabla-libro td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--linea)}
.tabla-libro th{color:var(--suave);font-weight:600;font-size:.82rem}
.visor{width:min(1000px,96vw);height:92vh;max-width:none;padding:0;border:1px solid var(--linea);border-radius:12px;
 background:var(--superficie);color:var(--tinta);overflow:hidden}
.visor[open]{display:flex;flex-direction:column}
.visor::backdrop{background:rgba(0,0,0,.7)}
.visor-barra{display:flex;align-items:center;gap:14px;padding:10px 14px;border-bottom:1px solid var(--linea);font-size:.9rem}
.visor-titulo{flex:1;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.visor-cerrar{font:inherit;cursor:pointer;padding:5px 12px;border-radius:8px;border:1px solid var(--linea);background:var(--superficie2);color:var(--tinta)}
.visor-marco{flex:1;min-height:0}
.visor-marco iframe{width:100%;height:100%;border:0;background:#fff}
.nivel-bloque{margin:18px 0 6px}
.nivel-bloque h3{display:flex;align-items:baseline;gap:10px;margin:18px 0 2px;font-size:1.05rem;color:var(--c)}
.nivel-bloque h3 small{font-weight:400;color:var(--suave);font-size:.84rem}
.compacta p{display:none}
.compacta{padding:13px 16px}
.num{font-size:.72rem;font-weight:700;color:var(--suave)}
.cabecera-card{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.esquema{margin:8px 0 8px 20px;padding:0}
.esquema li{margin:4px 0}
.nota-dato{color:#fbbf24;font-size:.82rem}
.ver-todos{display:inline-block;margin:2px 0 8px;font-weight:600}
.migas{margin:22px 0 0;font-size:.88rem}
.ficha-tec{display:grid;grid-template-columns:170px 1fr;gap:0;margin:12px 0;background:var(--superficie);
 border:1px solid var(--linea);border-radius:12px;overflow:hidden}
.ficha-tec dt,.ficha-tec dd{margin:0;padding:11px 14px;border-bottom:1px solid var(--linea)}
.ficha-tec dt{color:var(--suave);font-size:.85rem;font-weight:600;background:var(--superficie2)}
.ficha-tec dd:last-of-type,.ficha-tec dt:last-of-type{border-bottom:0}
ol.pasos{list-style:none;counter-reset:paso;margin:12px 0;padding:0}
ol.pasos>li{counter-increment:paso;position:relative;margin:12px 0;padding:14px 16px 12px 58px;background:var(--superficie);
 border:1px solid var(--linea);border-radius:12px}
ol.pasos>li::before{content:counter(paso);position:absolute;left:14px;top:14px;width:30px;height:30px;border-radius:50%;
 display:flex;align-items:center;justify-content:center;font-weight:800;color:#06122f;background:linear-gradient(135deg,#9be7ff,#3b82f6)}
ol.pasos h4{margin:0 0 6px;color:var(--tinta);font-size:1.02rem}
ol.pasos p{margin:4px 0;font-size:.93rem;max-width:none}
ol.pasos p b{color:var(--acento)}
.entrega{list-style:none;margin:8px 0;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px}
.entrega li{padding:10px 14px;border:1px dashed var(--linea);border-radius:10px;background:var(--superficie)}
.entrega li span{display:block;color:var(--suave);font-size:.85rem}
.sobre h3{color:var(--tinta);margin-top:24px}
.sobre ul{padding-left:20px}
.tambien{display:block;font-size:.78rem;color:var(--suave);margin-top:2px}
.tambien a{color:var(--suave);text-decoration:underline}
.chips.tiempo{margin:4px 0 8px}
.chip-tiempo{font:inherit;font-size:.82rem;cursor:pointer;padding:4px 12px;border-radius:999px;border:1px solid var(--linea);background:transparent;color:var(--suave)}
.chip-tiempo.activo{border-color:var(--acento);color:var(--acento);font-weight:600}
@media (max-width:560px){
 .subcols{grid-template-columns:1fr}
 .ficha-tec{grid-template-columns:1fr}.ficha-tec dt{border-bottom:0;padding-bottom:2px}
 .hero{gap:12px}.logo svg{width:60px;height:60px}.hero h1{font-size:1.85rem}
 .rejilla,.tarjetas{grid-template-columns:1fr}
 .panel{min-width:230px}
}

/* === REDISEÑO === */
.hero{display:grid;grid-template-columns:1.1fr 1fr;gap:26px;padding:26px;margin:10px 0 18px;border-radius:18px;border:1px solid var(--linea);
 background:radial-gradient(500px 240px at 0% 0%,rgba(56,189,248,.18),transparent 70%),radial-gradient(400px 240px at 100% 100%,rgba(167,139,250,.16),transparent 70%),var(--superficie)}
.hero h1,.hero h2.hero-t{font-size:1.9rem;line-height:1.15;margin:.2em 0 .3em;border:0;padding:0}
.hero .etq{display:inline-block;font-size:.72rem;letter-spacing:.1em;text-transform:uppercase;color:#38bdf8;font-weight:700}
.hero .sub{color:var(--suave);margin:0 0 6px}
.hero .chips2{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}
.hero .chip2{padding:3px 11px;border-radius:99px;border:1px solid;font-size:.8rem}
.hero .cta{display:inline-block;margin-top:10px;padding:9px 18px;border-radius:999px;background:#4ade80;color:#04121f;font-weight:800}
.hero .flujo-h svg{width:100%;height:auto}
.ap{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:12px 0}
.ap div{padding:14px 12px;border-radius:14px;background:var(--superficie);border:1px solid var(--linea);text-align:center;font-size:.88rem;position:relative;overflow:hidden}
.ap div::before{content:"";position:absolute;inset:0 0 auto 0;height:3px;background:var(--c)}
.ap i{display:block;font-style:normal;font-size:1.6rem;margin-bottom:4px}
.ap-t{margin:16px 0 0;font-size:1.05rem;color:#4ade80}
.red{padding:16px;margin:12px 0;border-radius:16px;border:1px solid var(--linea);background:var(--superficie)}
.red svg{width:100%;height:auto;display:block}
.red p{margin:6px 0 0;font-size:.86rem;color:var(--suave)}
.red a{cursor:pointer}
.gauge-b{max-width:230px;margin:12px auto;padding:14px;border-radius:16px;background:var(--superficie);border:1px solid var(--linea);text-align:center}
.gauge-b svg{width:100%;height:auto}
.gauge-b small{color:var(--suave);font-size:.85rem}
@media(max-width:760px){.hero{grid-template-columns:1fr}}
.aprenderas{margin:14px 0;padding:16px 20px;border:1px solid #4ade8055;border-left:4px solid #4ade80;border-radius:10px;
 background:rgba(74,222,128,.06)}
.aprenderas h3{margin:0 0 8px;font-size:1.05rem;color:#4ade80}
.aprenderas ul{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:4px 22px}
.aprenderas li{padding-left:24px;position:relative;font-size:.95rem}
.aprenderas li::before{content:"✓";position:absolute;left:0;color:#4ade80;font-weight:700}
.prog{display:flex;align-items:center;gap:10px;margin:8px 0 12px;font-size:.9rem;color:var(--suave)}
.prog-barra{flex:0 1 220px;height:8px;border-radius:99px;background:var(--linea);overflow:hidden}
.prog-barra i{display:block;height:100%;width:0;background:#4ade80;transition:width .3s}
.hecho-marca{display:none;margin-left:8px;padding:1px 9px;border-radius:99px;font-size:.78rem;font-weight:600;
 color:#052e16;background:#4ade80}
li.hecho .hecho-marca{display:inline-block}
.enlace-paso{display:inline-block;margin:8px 0 2px;padding:8px 14px;border-radius:8px;font-weight:600;font-size:.92rem;
 background:rgba(56,189,248,.12);border:1px solid #38bdf866;text-decoration:none}
.enlace-paso:hover{background:rgba(56,189,248,.22)}
.paso-pag h3.sec{margin:26px 0 8px;font-size:1.12rem;color:var(--tinta);border-bottom:1px solid var(--linea);padding-bottom:4px}
.paso-pag h3.sec .pag{float:right;font-size:.78rem;font-weight:400;color:var(--suave)}
.paso-pag p,.paso-pag li{max-width:72ch}
.paso-pag .fuente{color:var(--suave);font-size:.88rem;margin:0 0 6px}
.callout{margin:12px 0;padding:10px 14px;border-radius:8px;border-left:4px solid #38bdf8;background:rgba(56,189,248,.07);max-width:72ch}
.callout b{display:block;margin-bottom:2px;font-size:.78rem;letter-spacing:.06em;text-transform:uppercase;color:#38bdf8}
.callout.atencion{border-color:#fbbf24;background:rgba(251,191,36,.08)}.callout.atencion b{color:#fbbf24}
.callout.nota{border-color:#a78bfa;background:rgba(167,139,250,.08)}.callout.nota b{color:#a78bfa}
.callout.regla{border-color:#4ade80;background:rgba(74,222,128,.08)}.callout.regla b{color:#4ade80}
.tabla-scroll{overflow-x:auto;margin:10px 0}
.tabla-libro td.num,.tabla-libro th.num{text-align:right;font-variant-numeric:tabular-nums}
.tabla-libro tfoot td{font-weight:600;border-top:2px solid var(--linea)}
.tabla-nota{font-size:.88rem;color:var(--suave);margin:2px 0 10px}
details.codigo{margin:10px 0;border:1px solid var(--linea);border-radius:8px;background:var(--superficie)}
details.codigo summary{cursor:pointer;padding:8px 12px;font-size:.88rem;font-weight:600;color:#38bdf8}
pre.cod{margin:0;padding:12px 14px;overflow-x:auto;font-size:.82rem;line-height:1.5;border-top:1px solid var(--linea);
 font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
pre.salida{margin:0 0 10px;padding:10px 14px;overflow-x:auto;font-size:.82rem;line-height:1.5;border-radius:8px;
 background:#0a1a12;border:1px solid #4ade8044;color:#bbf7d0;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
.etiqueta-salida{margin:8px 0 2px;font-size:.78rem;letter-spacing:.06em;text-transform:uppercase;color:#4ade80;font-weight:600}
.copiar{float:right;margin:6px 8px;padding:3px 10px;font-size:.78rem;border-radius:6px;border:1px solid var(--linea);
 background:transparent;color:var(--suave);cursor:pointer}
figure.fig{margin:14px 0;padding:12px;border:1px solid var(--linea);border-radius:10px;background:var(--superficie);max-width:560px}
figure.fig svg{width:100%;height:auto;display:block}
figure.fig figcaption{font-size:.84rem;color:var(--suave);margin-top:8px}
.caja-paso{margin:26px 0;padding:16px 18px;border:1px solid var(--linea);border-radius:12px;background:var(--superficie)}
.caja-paso h2{margin-top:0}
.pregunta{margin:16px 0;padding:12px 14px;border:1px solid var(--linea);border-radius:10px}
.pregunta p{margin:0 0 8px;font-weight:600;max-width:none}
.pregunta label{display:block;margin:5px 0;padding:6px 10px;border-radius:8px;border:1px solid var(--linea);cursor:pointer;font-size:.95rem}
.pregunta label:hover{border-color:#38bdf8}
.pregunta input{margin-right:8px}
.pregunta.ok label.marcada{border-color:#4ade80;background:rgba(74,222,128,.12)}
.pregunta.mal label.marcada{border-color:#fb7185;background:rgba(251,113,133,.12)}
.pregunta label.correcta{border-color:#4ade80}
.pregunta .exp{margin:8px 0 0;font-size:.88rem;color:var(--suave);font-weight:400}
.resultado{margin:14px 0;padding:12px 16px;border-radius:10px;font-weight:600}
.resultado.bien{background:rgba(74,222,128,.12);border:1px solid #4ade80}
.resultado.regular{background:rgba(251,191,36,.1);border:1px solid #fbbf24}
.boton{display:inline-block;margin:6px 8px 0 0;padding:9px 16px;border-radius:8px;border:1px solid #38bdf8;background:rgba(56,189,248,.14);
 color:var(--tinta);font-weight:600;font-size:.92rem;cursor:pointer}
.boton:hover{background:rgba(56,189,248,.26)}
.boton.verde{border-color:#4ade80;background:rgba(74,222,128,.14)}
.boton:disabled{opacity:.5;cursor:default}
.evid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px;margin:12px 0}
.evid figure{margin:0;padding:10px;border:1px solid var(--linea);border-radius:10px;background:var(--bg)}
.evid img{max-width:100%;height:auto;border-radius:6px;display:block}
.evid figcaption{font-size:.84rem;color:var(--suave);margin-top:6px}
.evid-vacia{padding:12px 14px;border:1px dashed var(--linea);border-radius:10px;font-size:.92rem;color:var(--suave)}
.evid-vacia code,.paso-pag code.nombre{background:rgba(148,163,184,.15);padding:1px 6px;border-radius:5px;font-size:.84rem;word-break:break-all}
.nav-pasos{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;margin:20px 0}
@media print{
 .caja-paso{break-inside:avoid}
 .copiar,.boton,.nav-pasos{display:none!important}
 .fig-svg text{fill:#000!important}.fig-svg line{stroke:#555!important}.fig-svg circle{fill:#999!important;stroke:#000!important}
 details.codigo>summary{display:none}
 pre.cod,pre.salida{white-space:pre-wrap;border:1px solid #bbb!important}
}
.labr{margin:16px 0;padding:18px;border-radius:16px;border:1px solid #4ade8066;
 background:radial-gradient(520px 220px at 100% 0%,rgba(74,222,128,.11),transparent 70%),var(--superficie)}
.labr h3{margin:0 0 4px;font-size:1.05rem}
.labr .labr-sub{margin:0 0 12px;color:var(--suave);font-size:.9rem;max-width:none}
.labr-cuerpo{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(240px,1fr);gap:18px;align-items:start}
.labr canvas{width:100%;display:block;border-radius:12px;border:1px solid var(--linea);background:#0a1626;touch-action:none}
.labr-ctl label{display:flex;justify-content:space-between;font-size:.9rem;margin-top:10px}
.labr-ctl label b{color:var(--acento);font-family:ui-monospace,Menlo,Consolas,monospace}
.labr-ctl input[type=range]{width:100%;accent-color:#38bdf8}
.labr-ctl .chk{display:flex;gap:8px;align-items:flex-start;margin-top:10px;font-size:.85rem;color:var(--suave)}
.labr-ctl select{margin-top:6px;width:100%;padding:6px 8px;border-radius:8px;background:var(--superficie2);color:var(--tinta);border:1px solid var(--linea)}
.labr-kpis{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px}
.labr-kpi{padding:8px 10px;border-radius:10px;background:var(--superficie2);text-align:center}
.labr-kpi small{display:block;color:var(--suave);font-size:.68rem;text-transform:uppercase;letter-spacing:.07em}
.labr-kpi strong{font:800 1.15rem ui-monospace,Menlo,Consolas,monospace}
.labr-eq{margin-top:12px;padding:10px;text-align:center;border-radius:10px;background:#0a1626;border:1px dashed #38bdf866;
 font:700 1rem ui-monospace,Menlo,Consolas,monospace}
.labr-barra{height:8px;border-radius:99px;background:var(--linea);overflow:hidden;margin-top:6px}
.labr-barra i{display:block;height:100%;width:50%;background:#4ade80;transition:width .15s,background .15s}
.labr-msg{margin-top:10px;font-size:.88rem;color:var(--suave);min-height:2.8em}
.labr-falta{padding:14px;border:1px dashed var(--linea);border-radius:10px;color:var(--suave);font-size:.9rem}
@media(max-width:760px){.labr-cuerpo{grid-template-columns:1fr}}
@media print{.labr-ctl{display:none!important}.labr canvas{border:1px solid #888!important}}
.cards4{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px;margin:12px 0}
.cards4>div{padding:12px 14px;border-radius:12px;background:var(--superficie2);border-top:3px solid var(--c);font-size:.92rem}
.cards4 b{display:block;color:var(--c);font-size:.74rem;letter-spacing:.08em;text-transform:uppercase;margin-bottom:3px}
table.lineas td:first-child{font-family:ui-monospace,Menlo,Consolas,monospace;white-space:pre-wrap;color:#7dd3fc;font-size:.84rem;width:44%;vertical-align:top}
.colab{margin:12px 0;padding:14px 16px;border-radius:12px;border:1px solid #fbbf2466;background:rgba(251,191,36,.07)}
.colab ol{margin:8px 0 0;padding-left:20px;font-size:.92rem}
.colab a.boton{text-decoration:none;color:var(--tinta)}
.esperado{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin:10px 0}
.esp{padding:10px 12px;border-radius:10px;border:1px solid #4ade8066;background:rgba(74,222,128,.07)}
.esp small{display:block;color:var(--suave);font-size:.72rem;text-transform:uppercase;letter-spacing:.07em}
.esp strong{font:800 1.1rem ui-monospace,Menlo,Consolas,monospace;color:#4ade80}
.res4{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:12px 0}
.res4>div{padding:14px;border-radius:14px;background:var(--superficie);border:1px solid var(--linea);text-align:center}
.res4 strong{display:block;font:800 1.7rem ui-monospace,Menlo,Consolas,monospace;color:var(--c)}
.res4 small{color:var(--suave);font-size:.8rem}
.sec-paso{margin:30px 0}
.cpp{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin:14px 0 6px}
.cpp div{padding:12px 14px;border-radius:12px;background:var(--superficie2);border-top:3px solid var(--c);font-size:.92rem}
.cpp b{display:block;color:var(--c);font-size:.74rem;letter-spacing:.08em;text-transform:uppercase;margin-bottom:3px}
.kpis-g{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:14px 0}
.kpi-g{padding:16px 12px;border-radius:14px;background:var(--superficie);border:1px solid var(--linea);text-align:center;border-top:3px solid var(--c)}
.kpi-g strong{display:block;font:800 1.9rem ui-monospace,Menlo,Consolas,monospace;color:var(--c)}
.kpi-g small{display:block;color:var(--suave);font-size:.82rem;margin-top:2px}
table.glosa{width:100%;border-collapse:collapse;margin:10px 0;font-size:.9rem}
table.glosa td{padding:7px 10px;border-bottom:1px solid var(--linea);vertical-align:top}
table.glosa td:first-child{width:42%;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.82rem;color:#7dd3fc;word-break:break-word}
.btn-colab{display:inline-block;margin:6px 0;padding:11px 20px;border-radius:10px;font-weight:700;color:#04121f!important;
 background:linear-gradient(90deg,#fbbf24,#fb923c);text-decoration:none!important}
.btn-colab:hover{filter:brightness(1.08)}
.pasos-img{max-width:100%;height:auto;border-radius:10px;border:1px solid var(--linea);display:block}
@media print{table.glosa td:first-child{color:#000!important}.btn-colab{display:none!important}}
.leer{display:grid;gap:9px;margin:12px 0 22px;padding:14px 16px;border-radius:14px;border:1px solid var(--linea);background:var(--superficie)}
.leer>div{display:grid;grid-template-columns:150px 1fr;gap:10px;font-size:.93rem;max-width:none}
.leer b{font-size:.74rem;letter-spacing:.07em;text-transform:uppercase;color:var(--c);padding-top:2px}
.leer .ojo{padding:8px 12px;border-radius:8px;border-left:4px solid #fbbf24;background:rgba(251,191,36,.08);grid-template-columns:1fr}
.estaticos{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px;margin:12px 0}
.estaticos figure{margin:0;padding:10px;border:1px solid var(--linea);border-radius:12px;background:var(--superficie)}
.estaticos figure.este{border-color:#4ade80;box-shadow:0 0 0 1px #4ade8055}
.estaticos svg{width:100%;height:auto;display:block}
.estaticos figcaption{font-size:.84rem;color:var(--suave);margin-top:6px}
.estaticos figcaption b{color:var(--tinta)}
.flujo-svg{width:100%;max-width:760px;height:auto;display:block;margin:10px 0}
@media(max-width:640px){.leer>div{grid-template-columns:1fr;gap:2px}}
@media print{.leer b{color:#000!important}.estaticos svg text{fill:#000!important}.estaticos svg line,.estaticos svg path{stroke:#444!important}.flujo-svg text{fill:#000!important}}
@media print{
 *{background:#fff!important;color:#000!important;box-shadow:none!important;
   border-color:#bbb!important;text-shadow:none!important;transform:none!important}
 .barra,.buscador,.chips,.boton-mas,.logo,.enlace-tema,.mas{display:none!important}
 body{font-size:11pt}
 a{text-decoration:underline}
 .rejilla,.tarjetas,.cats{display:block}
 .subcols{display:block}
 .tema-card,.bloque-resumen,.proyecto,ol.pasos>li{break-inside:avoid;margin-bottom:12px}
 .chips.tiempo,.proyecto a.ir::after,.visor{display:none!important}
 ol.pasos>li::before{background:#fff!important;border:1px solid #000}
 li.item{break-inside:avoid}
}
"""

LOGO_SVG = '<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Logotipo"><defs><linearGradient id="lt" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#2b6cd6" stop-opacity=".62"/><stop offset="1" stop-color="#123a8f" stop-opacity=".38"/></linearGradient><linearGradient id="li" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0f3a8a" stop-opacity=".5"/><stop offset="1" stop-color="#091a47" stop-opacity=".7"/></linearGradient><linearGradient id="ld" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#16408f" stop-opacity=".45"/><stop offset="1" stop-color="#06122f" stop-opacity=".75"/></linearGradient><linearGradient id="lc" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#3b82f6" stop-opacity=".85"/><stop offset="1" stop-color="#0c2a6b" stop-opacity=".85"/></linearGradient><linearGradient id="lb" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#bff3ff"/><stop offset=".55" stop-color="#38bdf8"/><stop offset="1" stop-color="#3b82f6"/></linearGradient><linearGradient id="lg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#e6fbff"/><stop offset=".5" stop-color="#5ad1ff"/><stop offset="1" stop-color="#2f7be8"/></linearGradient><radialGradient id="ln" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#fff"/><stop offset=".45" stop-color="#9eeaff"/><stop offset="1" stop-color="#38bdf8" stop-opacity="0"/></radialGradient><filter id="lh" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="1.6"/></filter><filter id="ls" x="-40%" y="-100%" width="180%" height="300%"><feGaussianBlur stdDeviation="2"/></filter></defs><ellipse cx="32" cy="62.2" rx="17" ry="1.8" fill="#000" opacity=".4" filter="url(#ls)"/><polygon points="8.50,14.69 38.30,8.25 38.30,40.15 8.50,46.59" fill="url(#ld)" opacity="1"/><polygon points="38.30,8.25 38.30,40.15 55.50,51.31 55.50,19.41" fill="url(#lt)" opacity="1"/><polygon points="8.50,46.59 38.30,40.15 55.50,51.31 25.70,57.75" fill="url(#li)" opacity="1"/><line x1="8.50" y1="14.69" x2="20.80" y2="24.27" stroke="#8fe6ff" stroke-width=".7" opacity=".75"/><line x1="25.70" y1="25.85" x2="29.00" y2="29.59" stroke="#8fe6ff" stroke-width=".7" opacity=".75"/><line x1="8.50" y1="46.59" x2="20.80" y2="39.48" stroke="#8fe6ff" stroke-width=".7" opacity=".75"/><line x1="25.70" y1="57.75" x2="29.00" y2="44.80" stroke="#8fe6ff" stroke-width=".7" opacity=".75"/><line x1="38.30" y1="8.25" x2="35.00" y2="21.20" stroke="#8fe6ff" stroke-width=".7" opacity=".75"/><line x1="55.50" y1="19.41" x2="43.20" y2="26.52" stroke="#8fe6ff" stroke-width=".7" opacity=".75"/><line x1="38.30" y1="40.15" x2="35.00" y2="36.41" stroke="#8fe6ff" stroke-width=".7" opacity=".75"/><line x1="55.50" y1="51.31" x2="43.20" y2="41.73" stroke="#8fe6ff" stroke-width=".7" opacity=".75"/><line x1="14.65" y1="19.48" x2="27.35" y2="27.72" stroke="#8fe6ff" stroke-width=".55" opacity=".7"/><line x1="14.65" y1="19.48" x2="14.65" y2="43.03" stroke="#8fe6ff" stroke-width=".55" opacity=".7"/><line x1="14.65" y1="19.48" x2="36.65" y2="14.73" stroke="#8fe6ff" stroke-width=".55" opacity=".7"/><line x1="27.35" y1="27.72" x2="27.35" y2="51.27" stroke="#8fe6ff" stroke-width=".55" opacity=".7"/><line x1="27.35" y1="27.72" x2="49.35" y2="22.97" stroke="#8fe6ff" stroke-width=".55" opacity=".7"/><line x1="14.65" y1="43.03" x2="27.35" y2="51.27" stroke="#8fe6ff" stroke-width=".55" opacity=".7"/><line x1="14.65" y1="43.03" x2="36.65" y2="38.28" stroke="#8fe6ff" stroke-width=".55" opacity=".7"/><line x1="27.35" y1="51.27" x2="49.35" y2="46.52" stroke="#8fe6ff" stroke-width=".55" opacity=".7"/><line x1="36.65" y1="14.73" x2="49.35" y2="22.97" stroke="#8fe6ff" stroke-width=".55" opacity=".7"/><line x1="36.65" y1="14.73" x2="36.65" y2="38.28" stroke="#8fe6ff" stroke-width=".55" opacity=".7"/><line x1="49.35" y1="22.97" x2="49.35" y2="46.52" stroke="#8fe6ff" stroke-width=".55" opacity=".7"/><line x1="36.65" y1="38.28" x2="49.35" y2="46.52" stroke="#8fe6ff" stroke-width=".55" opacity=".7"/><polygon points="20.80,24.27 35.00,21.20 35.00,36.41 20.80,39.48" fill="url(#lc)" opacity="0.55"/><polygon points="35.00,21.20 35.00,36.41 43.20,41.73 43.20,26.52" fill="url(#lc)" opacity="0.55"/><polygon points="20.80,39.48 35.00,36.41 43.20,41.73 29.00,44.80" fill="url(#lc)" opacity="0.55"/><polygon points="20.80,24.27 35.00,21.20 43.20,26.52 29.00,29.59" fill="url(#lc)" opacity="0.35"/><polygon points="20.80,24.27 20.80,39.48 29.00,44.80 29.00,29.59" fill="url(#lc)" opacity="0.35"/><polygon points="29.00,29.59 43.20,26.52 43.20,41.73 29.00,44.80" fill="url(#lc)" opacity="0.35"/><line x1="20.80" y1="24.27" x2="29.00" y2="29.59" stroke="url(#lb)" stroke-width=".9" opacity=".95"/><line x1="20.80" y1="24.27" x2="20.80" y2="39.48" stroke="url(#lb)" stroke-width=".9" opacity=".95"/><line x1="20.80" y1="24.27" x2="35.00" y2="21.20" stroke="url(#lb)" stroke-width=".9" opacity=".95"/><line x1="29.00" y1="29.59" x2="29.00" y2="44.80" stroke="url(#lb)" stroke-width=".9" opacity=".95"/><line x1="29.00" y1="29.59" x2="43.20" y2="26.52" stroke="url(#lb)" stroke-width=".9" opacity=".95"/><line x1="20.80" y1="39.48" x2="29.00" y2="44.80" stroke="url(#lb)" stroke-width=".9" opacity=".95"/><line x1="20.80" y1="39.48" x2="35.00" y2="36.41" stroke="url(#lb)" stroke-width=".9" opacity=".95"/><line x1="29.00" y1="44.80" x2="43.20" y2="41.73" stroke="url(#lb)" stroke-width=".9" opacity=".95"/><line x1="35.00" y1="21.20" x2="43.20" y2="26.52" stroke="url(#lb)" stroke-width=".9" opacity=".95"/><line x1="35.00" y1="21.20" x2="35.00" y2="36.41" stroke="url(#lb)" stroke-width=".9" opacity=".95"/><line x1="43.20" y1="26.52" x2="43.20" y2="41.73" stroke="url(#lb)" stroke-width=".9" opacity=".95"/><line x1="35.00" y1="36.41" x2="43.20" y2="41.73" stroke="url(#lb)" stroke-width=".9" opacity=".95"/><polygon points="8.50,14.69 38.30,8.25 55.50,19.41 25.70,25.85" fill="url(#li)" opacity="0.4"/><polygon points="8.50,14.69 8.50,46.59 25.70,57.75 25.70,25.85" fill="url(#lt)" opacity="0.4"/><polygon points="25.70,25.85 55.50,19.41 55.50,51.31 25.70,57.75" fill="url(#ld)" opacity="0.4"/><circle cx="32" cy="33" r="8" fill="#38bdf8" opacity=".5" filter="url(#lh)"/><path d="M36.12 32.18 L37.57 32.39 L37.57 33.61 L36.12 33.82 L35.49 35.33 L36.37 36.50 L35.50 37.37 L34.33 36.49 L32.82 37.12 L32.61 38.57 L31.39 38.57 L31.18 37.12 L29.67 36.49 L28.50 37.37 L27.63 36.50 L28.51 35.33 L27.88 33.82 L26.43 33.61 L26.43 32.39 L27.88 32.18 L28.51 30.67 L27.63 29.50 L28.50 28.63 L29.67 29.51 L31.18 28.88 L31.39 27.43 L32.61 27.43 L32.82 28.88 L34.33 29.51 L35.50 28.63 L36.37 29.50 L35.49 30.67 Z M33.60 33.00 A1.6 1.6 0 1 0 30.40 33.00 A1.6 1.6 0 1 0 33.60 33.00 Z" fill="url(#lg)" fill-rule="evenodd" stroke="#e6fbff" stroke-width=".35" stroke-linejoin="round"/><circle cx="8.50" cy="14.69" r="3.7" fill="url(#ln)" opacity=".8"/><circle cx="8.50" cy="14.69" r="1.6" fill="#fff"/><circle cx="14.65" cy="19.48" r="2.5" fill="url(#ln)" opacity=".8"/><circle cx="14.65" cy="19.48" r="1.1" fill="#fff"/><circle cx="20.80" cy="24.27" r="3.0" fill="url(#ln)" opacity=".8"/><circle cx="20.80" cy="24.27" r="1.3" fill="#fff"/><circle cx="25.70" cy="25.85" r="3.7" fill="url(#ln)" opacity=".8"/><circle cx="25.70" cy="25.85" r="1.6" fill="#fff"/><circle cx="27.35" cy="27.72" r="2.5" fill="url(#ln)" opacity=".8"/><circle cx="27.35" cy="27.72" r="1.1" fill="#fff"/><circle cx="29.00" cy="29.59" r="3.0" fill="url(#ln)" opacity=".8"/><circle cx="29.00" cy="29.59" r="1.3" fill="#fff"/><circle cx="8.50" cy="46.59" r="3.7" fill="url(#ln)" opacity=".8"/><circle cx="8.50" cy="46.59" r="1.6" fill="#fff"/><circle cx="14.65" cy="43.03" r="2.5" fill="url(#ln)" opacity=".8"/><circle cx="14.65" cy="43.03" r="1.1" fill="#fff"/><circle cx="20.80" cy="39.48" r="3.0" fill="url(#ln)" opacity=".8"/><circle cx="20.80" cy="39.48" r="1.3" fill="#fff"/><circle cx="25.70" cy="57.75" r="3.7" fill="url(#ln)" opacity=".8"/><circle cx="25.70" cy="57.75" r="1.6" fill="#fff"/><circle cx="27.35" cy="51.27" r="2.5" fill="url(#ln)" opacity=".8"/><circle cx="27.35" cy="51.27" r="1.1" fill="#fff"/><circle cx="29.00" cy="44.80" r="3.0" fill="url(#ln)" opacity=".8"/><circle cx="29.00" cy="44.80" r="1.3" fill="#fff"/><circle cx="38.30" cy="8.25" r="3.7" fill="url(#ln)" opacity=".8"/><circle cx="38.30" cy="8.25" r="1.6" fill="#fff"/><circle cx="36.65" cy="14.73" r="2.5" fill="url(#ln)" opacity=".8"/><circle cx="36.65" cy="14.73" r="1.1" fill="#fff"/><circle cx="35.00" cy="21.20" r="3.0" fill="url(#ln)" opacity=".8"/><circle cx="35.00" cy="21.20" r="1.3" fill="#fff"/><circle cx="55.50" cy="19.41" r="3.7" fill="url(#ln)" opacity=".8"/><circle cx="55.50" cy="19.41" r="1.6" fill="#fff"/><circle cx="49.35" cy="22.97" r="2.5" fill="url(#ln)" opacity=".8"/><circle cx="49.35" cy="22.97" r="1.1" fill="#fff"/><circle cx="43.20" cy="26.52" r="3.0" fill="url(#ln)" opacity=".8"/><circle cx="43.20" cy="26.52" r="1.3" fill="#fff"/><circle cx="38.30" cy="40.15" r="3.7" fill="url(#ln)" opacity=".8"/><circle cx="38.30" cy="40.15" r="1.6" fill="#fff"/><circle cx="36.65" cy="38.28" r="2.5" fill="url(#ln)" opacity=".8"/><circle cx="36.65" cy="38.28" r="1.1" fill="#fff"/><circle cx="35.00" cy="36.41" r="3.0" fill="url(#ln)" opacity=".8"/><circle cx="35.00" cy="36.41" r="1.3" fill="#fff"/><circle cx="55.50" cy="51.31" r="3.7" fill="url(#ln)" opacity=".8"/><circle cx="55.50" cy="51.31" r="1.6" fill="#fff"/><circle cx="49.35" cy="46.52" r="2.5" fill="url(#ln)" opacity=".8"/><circle cx="49.35" cy="46.52" r="1.1" fill="#fff"/><circle cx="43.20" cy="41.73" r="3.0" fill="url(#ln)" opacity=".8"/><circle cx="43.20" cy="41.73" r="1.3" fill="#fff"/><line x1="8.50" y1="14.69" x2="25.70" y2="25.85" stroke="url(#lb)" stroke-width="1.5" stroke-linecap="round" opacity="1"/><line x1="8.50" y1="14.69" x2="8.50" y2="46.59" stroke="url(#lb)" stroke-width="0.9" stroke-linecap="round" opacity="0.6"/><line x1="8.50" y1="14.69" x2="38.30" y2="8.25" stroke="url(#lb)" stroke-width="0.9" stroke-linecap="round" opacity="0.6"/><line x1="25.70" y1="25.85" x2="25.70" y2="57.75" stroke="url(#lb)" stroke-width="1.5" stroke-linecap="round" opacity="1"/><line x1="25.70" y1="25.85" x2="55.50" y2="19.41" stroke="url(#lb)" stroke-width="1.5" stroke-linecap="round" opacity="1"/><line x1="8.50" y1="46.59" x2="25.70" y2="57.75" stroke="url(#lb)" stroke-width="1.5" stroke-linecap="round" opacity="1"/><line x1="8.50" y1="46.59" x2="38.30" y2="40.15" stroke="url(#lb)" stroke-width="0.9" stroke-linecap="round" opacity="0.6"/><line x1="25.70" y1="57.75" x2="55.50" y2="51.31" stroke="url(#lb)" stroke-width="1.5" stroke-linecap="round" opacity="1"/><line x1="38.30" y1="8.25" x2="55.50" y2="19.41" stroke="url(#lb)" stroke-width="0.9" stroke-linecap="round" opacity="0.6"/><line x1="38.30" y1="8.25" x2="38.30" y2="40.15" stroke="url(#lb)" stroke-width="0.9" stroke-linecap="round" opacity="0.6"/><line x1="55.50" y1="19.41" x2="55.50" y2="51.31" stroke="url(#lb)" stroke-width="1.5" stroke-linecap="round" opacity="1"/><line x1="38.30" y1="40.15" x2="55.50" y2="51.31" stroke="url(#lb)" stroke-width="0.9" stroke-linecap="round" opacity="0.6"/></svg>'

FAVICON_SVG = '<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Logotipo"><defs><linearGradient id="lt" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#2b6cd6" stop-opacity=".62"/><stop offset="1" stop-color="#123a8f" stop-opacity=".38"/></linearGradient><linearGradient id="li" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0f3a8a" stop-opacity=".5"/><stop offset="1" stop-color="#091a47" stop-opacity=".7"/></linearGradient><linearGradient id="ld" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#16408f" stop-opacity=".45"/><stop offset="1" stop-color="#06122f" stop-opacity=".75"/></linearGradient><linearGradient id="lc" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#3b82f6" stop-opacity=".85"/><stop offset="1" stop-color="#0c2a6b" stop-opacity=".85"/></linearGradient><linearGradient id="lb" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#bff3ff"/><stop offset=".55" stop-color="#38bdf8"/><stop offset="1" stop-color="#3b82f6"/></linearGradient><linearGradient id="lg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#e6fbff"/><stop offset=".5" stop-color="#5ad1ff"/><stop offset="1" stop-color="#2f7be8"/></linearGradient><radialGradient id="ln" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#fff"/><stop offset=".45" stop-color="#9eeaff"/><stop offset="1" stop-color="#38bdf8" stop-opacity="0"/></radialGradient><filter id="lh" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="1.6"/></filter><filter id="ls" x="-40%" y="-100%" width="180%" height="300%"><feGaussianBlur stdDeviation="2"/></filter></defs><rect width="64" height="64" rx="14" fill="#0b1220"/><polygon points="8.50,14.69 38.30,8.25 38.30,40.15 8.50,46.59" fill="url(#ld)" opacity="1"/><polygon points="38.30,8.25 38.30,40.15 55.50,51.31 55.50,19.41" fill="url(#lt)" opacity="1"/><polygon points="8.50,46.59 38.30,40.15 55.50,51.31 25.70,57.75" fill="url(#li)" opacity="1"/><line x1="8.50" y1="14.69" x2="20.80" y2="24.27" stroke="#8fe6ff" stroke-width=".7" opacity=".75"/><line x1="25.70" y1="25.85" x2="29.00" y2="29.59" stroke="#8fe6ff" stroke-width=".7" opacity=".75"/><line x1="8.50" y1="46.59" x2="20.80" y2="39.48" stroke="#8fe6ff" stroke-width=".7" opacity=".75"/><line x1="25.70" y1="57.75" x2="29.00" y2="44.80" stroke="#8fe6ff" stroke-width=".7" opacity=".75"/><line x1="38.30" y1="8.25" x2="35.00" y2="21.20" stroke="#8fe6ff" stroke-width=".7" opacity=".75"/><line x1="55.50" y1="19.41" x2="43.20" y2="26.52" stroke="#8fe6ff" stroke-width=".7" opacity=".75"/><line x1="38.30" y1="40.15" x2="35.00" y2="36.41" stroke="#8fe6ff" stroke-width=".7" opacity=".75"/><line x1="55.50" y1="51.31" x2="43.20" y2="41.73" stroke="#8fe6ff" stroke-width=".7" opacity=".75"/><line x1="14.65" y1="19.48" x2="27.35" y2="27.72" stroke="#8fe6ff" stroke-width=".55" opacity=".7"/><line x1="14.65" y1="19.48" x2="14.65" y2="43.03" stroke="#8fe6ff" stroke-width=".55" opacity=".7"/><line x1="14.65" y1="19.48" x2="36.65" y2="14.73" stroke="#8fe6ff" stroke-width=".55" opacity=".7"/><line x1="27.35" y1="27.72" x2="27.35" y2="51.27" stroke="#8fe6ff" stroke-width=".55" opacity=".7"/><line x1="27.35" y1="27.72" x2="49.35" y2="22.97" stroke="#8fe6ff" stroke-width=".55" opacity=".7"/><line x1="14.65" y1="43.03" x2="27.35" y2="51.27" stroke="#8fe6ff" stroke-width=".55" opacity=".7"/><line x1="14.65" y1="43.03" x2="36.65" y2="38.28" stroke="#8fe6ff" stroke-width=".55" opacity=".7"/><line x1="27.35" y1="51.27" x2="49.35" y2="46.52" stroke="#8fe6ff" stroke-width=".55" opacity=".7"/><line x1="36.65" y1="14.73" x2="49.35" y2="22.97" stroke="#8fe6ff" stroke-width=".55" opacity=".7"/><line x1="36.65" y1="14.73" x2="36.65" y2="38.28" stroke="#8fe6ff" stroke-width=".55" opacity=".7"/><line x1="49.35" y1="22.97" x2="49.35" y2="46.52" stroke="#8fe6ff" stroke-width=".55" opacity=".7"/><line x1="36.65" y1="38.28" x2="49.35" y2="46.52" stroke="#8fe6ff" stroke-width=".55" opacity=".7"/><polygon points="20.80,24.27 35.00,21.20 35.00,36.41 20.80,39.48" fill="url(#lc)" opacity="0.55"/><polygon points="35.00,21.20 35.00,36.41 43.20,41.73 43.20,26.52" fill="url(#lc)" opacity="0.55"/><polygon points="20.80,39.48 35.00,36.41 43.20,41.73 29.00,44.80" fill="url(#lc)" opacity="0.55"/><polygon points="20.80,24.27 35.00,21.20 43.20,26.52 29.00,29.59" fill="url(#lc)" opacity="0.35"/><polygon points="20.80,24.27 20.80,39.48 29.00,44.80 29.00,29.59" fill="url(#lc)" opacity="0.35"/><polygon points="29.00,29.59 43.20,26.52 43.20,41.73 29.00,44.80" fill="url(#lc)" opacity="0.35"/><line x1="20.80" y1="24.27" x2="29.00" y2="29.59" stroke="url(#lb)" stroke-width=".9" opacity=".95"/><line x1="20.80" y1="24.27" x2="20.80" y2="39.48" stroke="url(#lb)" stroke-width=".9" opacity=".95"/><line x1="20.80" y1="24.27" x2="35.00" y2="21.20" stroke="url(#lb)" stroke-width=".9" opacity=".95"/><line x1="29.00" y1="29.59" x2="29.00" y2="44.80" stroke="url(#lb)" stroke-width=".9" opacity=".95"/><line x1="29.00" y1="29.59" x2="43.20" y2="26.52" stroke="url(#lb)" stroke-width=".9" opacity=".95"/><line x1="20.80" y1="39.48" x2="29.00" y2="44.80" stroke="url(#lb)" stroke-width=".9" opacity=".95"/><line x1="20.80" y1="39.48" x2="35.00" y2="36.41" stroke="url(#lb)" stroke-width=".9" opacity=".95"/><line x1="29.00" y1="44.80" x2="43.20" y2="41.73" stroke="url(#lb)" stroke-width=".9" opacity=".95"/><line x1="35.00" y1="21.20" x2="43.20" y2="26.52" stroke="url(#lb)" stroke-width=".9" opacity=".95"/><line x1="35.00" y1="21.20" x2="35.00" y2="36.41" stroke="url(#lb)" stroke-width=".9" opacity=".95"/><line x1="43.20" y1="26.52" x2="43.20" y2="41.73" stroke="url(#lb)" stroke-width=".9" opacity=".95"/><line x1="35.00" y1="36.41" x2="43.20" y2="41.73" stroke="url(#lb)" stroke-width=".9" opacity=".95"/><polygon points="8.50,14.69 38.30,8.25 55.50,19.41 25.70,25.85" fill="url(#li)" opacity="0.4"/><polygon points="8.50,14.69 8.50,46.59 25.70,57.75 25.70,25.85" fill="url(#lt)" opacity="0.4"/><polygon points="25.70,25.85 55.50,19.41 55.50,51.31 25.70,57.75" fill="url(#ld)" opacity="0.4"/><circle cx="32" cy="33" r="8" fill="#38bdf8" opacity=".5" filter="url(#lh)"/><path d="M36.12 32.18 L37.57 32.39 L37.57 33.61 L36.12 33.82 L35.49 35.33 L36.37 36.50 L35.50 37.37 L34.33 36.49 L32.82 37.12 L32.61 38.57 L31.39 38.57 L31.18 37.12 L29.67 36.49 L28.50 37.37 L27.63 36.50 L28.51 35.33 L27.88 33.82 L26.43 33.61 L26.43 32.39 L27.88 32.18 L28.51 30.67 L27.63 29.50 L28.50 28.63 L29.67 29.51 L31.18 28.88 L31.39 27.43 L32.61 27.43 L32.82 28.88 L34.33 29.51 L35.50 28.63 L36.37 29.50 L35.49 30.67 Z M33.60 33.00 A1.6 1.6 0 1 0 30.40 33.00 A1.6 1.6 0 1 0 33.60 33.00 Z" fill="url(#lg)" fill-rule="evenodd" stroke="#e6fbff" stroke-width=".35" stroke-linejoin="round"/><circle cx="8.50" cy="14.69" r="3.7" fill="url(#ln)" opacity=".8"/><circle cx="8.50" cy="14.69" r="1.6" fill="#fff"/><circle cx="14.65" cy="19.48" r="2.5" fill="url(#ln)" opacity=".8"/><circle cx="14.65" cy="19.48" r="1.1" fill="#fff"/><circle cx="20.80" cy="24.27" r="3.0" fill="url(#ln)" opacity=".8"/><circle cx="20.80" cy="24.27" r="1.3" fill="#fff"/><circle cx="25.70" cy="25.85" r="3.7" fill="url(#ln)" opacity=".8"/><circle cx="25.70" cy="25.85" r="1.6" fill="#fff"/><circle cx="27.35" cy="27.72" r="2.5" fill="url(#ln)" opacity=".8"/><circle cx="27.35" cy="27.72" r="1.1" fill="#fff"/><circle cx="29.00" cy="29.59" r="3.0" fill="url(#ln)" opacity=".8"/><circle cx="29.00" cy="29.59" r="1.3" fill="#fff"/><circle cx="8.50" cy="46.59" r="3.7" fill="url(#ln)" opacity=".8"/><circle cx="8.50" cy="46.59" r="1.6" fill="#fff"/><circle cx="14.65" cy="43.03" r="2.5" fill="url(#ln)" opacity=".8"/><circle cx="14.65" cy="43.03" r="1.1" fill="#fff"/><circle cx="20.80" cy="39.48" r="3.0" fill="url(#ln)" opacity=".8"/><circle cx="20.80" cy="39.48" r="1.3" fill="#fff"/><circle cx="25.70" cy="57.75" r="3.7" fill="url(#ln)" opacity=".8"/><circle cx="25.70" cy="57.75" r="1.6" fill="#fff"/><circle cx="27.35" cy="51.27" r="2.5" fill="url(#ln)" opacity=".8"/><circle cx="27.35" cy="51.27" r="1.1" fill="#fff"/><circle cx="29.00" cy="44.80" r="3.0" fill="url(#ln)" opacity=".8"/><circle cx="29.00" cy="44.80" r="1.3" fill="#fff"/><circle cx="38.30" cy="8.25" r="3.7" fill="url(#ln)" opacity=".8"/><circle cx="38.30" cy="8.25" r="1.6" fill="#fff"/><circle cx="36.65" cy="14.73" r="2.5" fill="url(#ln)" opacity=".8"/><circle cx="36.65" cy="14.73" r="1.1" fill="#fff"/><circle cx="35.00" cy="21.20" r="3.0" fill="url(#ln)" opacity=".8"/><circle cx="35.00" cy="21.20" r="1.3" fill="#fff"/><circle cx="55.50" cy="19.41" r="3.7" fill="url(#ln)" opacity=".8"/><circle cx="55.50" cy="19.41" r="1.6" fill="#fff"/><circle cx="49.35" cy="22.97" r="2.5" fill="url(#ln)" opacity=".8"/><circle cx="49.35" cy="22.97" r="1.1" fill="#fff"/><circle cx="43.20" cy="26.52" r="3.0" fill="url(#ln)" opacity=".8"/><circle cx="43.20" cy="26.52" r="1.3" fill="#fff"/><circle cx="38.30" cy="40.15" r="3.7" fill="url(#ln)" opacity=".8"/><circle cx="38.30" cy="40.15" r="1.6" fill="#fff"/><circle cx="36.65" cy="38.28" r="2.5" fill="url(#ln)" opacity=".8"/><circle cx="36.65" cy="38.28" r="1.1" fill="#fff"/><circle cx="35.00" cy="36.41" r="3.0" fill="url(#ln)" opacity=".8"/><circle cx="35.00" cy="36.41" r="1.3" fill="#fff"/><circle cx="55.50" cy="51.31" r="3.7" fill="url(#ln)" opacity=".8"/><circle cx="55.50" cy="51.31" r="1.6" fill="#fff"/><circle cx="49.35" cy="46.52" r="2.5" fill="url(#ln)" opacity=".8"/><circle cx="49.35" cy="46.52" r="1.1" fill="#fff"/><circle cx="43.20" cy="41.73" r="3.0" fill="url(#ln)" opacity=".8"/><circle cx="43.20" cy="41.73" r="1.3" fill="#fff"/><line x1="8.50" y1="14.69" x2="25.70" y2="25.85" stroke="url(#lb)" stroke-width="1.5" stroke-linecap="round" opacity="1"/><line x1="8.50" y1="14.69" x2="8.50" y2="46.59" stroke="url(#lb)" stroke-width="0.9" stroke-linecap="round" opacity="0.6"/><line x1="8.50" y1="14.69" x2="38.30" y2="8.25" stroke="url(#lb)" stroke-width="0.9" stroke-linecap="round" opacity="0.6"/><line x1="25.70" y1="25.85" x2="25.70" y2="57.75" stroke="url(#lb)" stroke-width="1.5" stroke-linecap="round" opacity="1"/><line x1="25.70" y1="25.85" x2="55.50" y2="19.41" stroke="url(#lb)" stroke-width="1.5" stroke-linecap="round" opacity="1"/><line x1="8.50" y1="46.59" x2="25.70" y2="57.75" stroke="url(#lb)" stroke-width="1.5" stroke-linecap="round" opacity="1"/><line x1="8.50" y1="46.59" x2="38.30" y2="40.15" stroke="url(#lb)" stroke-width="0.9" stroke-linecap="round" opacity="0.6"/><line x1="25.70" y1="57.75" x2="55.50" y2="51.31" stroke="url(#lb)" stroke-width="1.5" stroke-linecap="round" opacity="1"/><line x1="38.30" y1="8.25" x2="55.50" y2="19.41" stroke="url(#lb)" stroke-width="0.9" stroke-linecap="round" opacity="0.6"/><line x1="38.30" y1="8.25" x2="38.30" y2="40.15" stroke="url(#lb)" stroke-width="0.9" stroke-linecap="round" opacity="0.6"/><line x1="55.50" y1="19.41" x2="55.50" y2="51.31" stroke="url(#lb)" stroke-width="1.5" stroke-linecap="round" opacity="1"/><line x1="38.30" y1="40.15" x2="55.50" y2="51.31" stroke="url(#lb)" stroke-width="0.9" stroke-linecap="round" opacity="0.6"/></svg>'

FAVICON = "data:image/svg+xml," + quote(FAVICON_SVG)

# ----------------------------------------------------------------- interactividad
JS = """
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
      function dibujaRes(){
        var W=cv.clientWidth, H=Math.round(W*0.5), dpr=window.devicePixelRatio||1;
        cv.width=W*dpr; cv.height=H*dpr; cv.style.height=H+'px'; cx.setTransform(dpr,0,0,dpr,0,0);
        var xs=[],rs=[],i,n=0,sr=0,sq=0,mx=0;
        for(i=0;i<N;i++){ if(!sel(i)) continue; var pr=mo*T[i]+bo, r=P[i]-pr; xs.push(pr); rs.push(r); n++; sr+=r; sq+=r*r; if(Math.abs(r)>mx) mx=Math.abs(r); }
        var media=sr/n, sd=Math.sqrt(sq/n-media*media);
        var xa=Math.min.apply(null,xs)-4, xb=Math.max.apply(null,xs)+4, ya=-Math.ceil(mx/5)*5-2, yb=Math.ceil(mx/5)*5+2;
        var L=54,Rr=12,Tt=12,Bb=40;
        var X=function(x){ return L+(x-xa)*(W-L-Rr)/(xb-xa); }, Y=function(y){ return H-Bb-(y-ya)*(H-Tt-Bb)/(yb-ya); };
        cx.clearRect(0,0,W,H); cx.font='11px sans-serif'; cx.strokeStyle='#1d2b44'; cx.lineWidth=1; cx.fillStyle='#8896ad';
        var k,v;
        for(k=-4;k<=4;k++){ v=k*Math.ceil(mx/20)*5; if(v<ya||v>yb) continue; cx.beginPath(); cx.moveTo(L,Y(v)); cx.lineTo(W-Rr,Y(v)); cx.stroke(); cx.textAlign='right'; cx.fillText(v,L-6,Y(v)+4); }
        for(k=0;k<=6;k++){ v=xa+(xb-xa)*k/6; cx.textAlign='center'; cx.fillText(Math.round(v),X(v),H-Bb+16); }
        cx.fillStyle='#cbd5e1'; cx.textAlign='center'; cx.fillText('Potencia predicha (MW)',(L+W-Rr)/2,H-6);
        cx.save(); cx.translate(13,(Tt+H-Bb)/2); cx.rotate(-Math.PI/2); cx.fillText('Residuo = real − predicho (MW)',0,0); cx.restore();
        cx.globalAlpha=0.3; cx.fillStyle='#38bdf8';
        for(i=0;i<xs.length;i++){ cx.beginPath(); cx.arc(X(xs[i]),Y(rs[i]),2,0,6.2832); cx.fill(); }
        cx.globalAlpha=1; cx.lineWidth=1.4; cx.setLineDash([5,4]); cx.strokeStyle='#fbbf24';
        [1.96*sd,-1.96*sd].forEach(function(y){ cx.beginPath(); cx.moveTo(L,Y(y)); cx.lineTo(W-Rr,Y(y)); cx.stroke(); });
        cx.fillStyle='#fbbf24'; cx.textAlign='left'; cx.fillText('±1,96·σ (≈95 % de los errores)',L+6,Y(1.96*sd)-5);
        cx.strokeStyle='#fb7185'; cx.lineWidth=2; cx.beginPath(); cx.moveTo(L,Y(0)); cx.lineTo(W-Rr,Y(0)); cx.stroke(); cx.setLineDash([]);
        cx.fillStyle='#fb7185'; cx.fillText('error cero',L+6,Y(0)-5);
        $('.k-n',box).textContent=fmt(n,0); $('.k-rm',box).textContent=fmt(media,2)+' MW';
        $('.k-rs',box).textContent=fmt(sd,2)+' MW'; $('.k-rx',box).textContent=fmt(mx,1)+' MW';
      }
      function pinta(){ if(modo==='residuos') dibujaRes(); else dibuja(); }
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
        } else if(modo==='nube'){
          var cu=calc(mo,bo);
          $('.k-n',box).textContent=fmt(cu.n,0);
          $('.k-cor',box).textContent=fmt(cor,3);
          $('.k-rt',box).textContent=fmt(tmin,1)+' a '+fmt(tmax,1)+' °C';
          $('.k-rp',box).textContent=fmt(pmin,0)+' a '+fmt(pmax,0)+' MW';
        }
        pinta();
      }
      [sM,sB,selG,chkPiv,chkRec].forEach(function(el){ if(el){ el.addEventListener('input',refresca); el.addEventListener('change',refresca); } });
      var bs=$('.b-sol',box); if(bs) bs.addEventListener('click',function(){ if(chkPiv) chkPiv.checked=false; sM.value=mo.toFixed(2); sB.value=bo.toFixed(1); refresca(); });
      var b0=$('.b-cero',box); if(b0) b0.addEventListener('click',function(){ sM.value=0; sB.value=ym.toFixed(1); if(chkPiv) chkPiv.checked=false; refresca(); });
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
        for(k=0;k<=5;k++){ v=y0+(y1-y0)*k/5; cx.beginPath(); cx.moveTo(l,Y(v)); cx.lineTo(W-r,Y(v)); cx.stroke(); cx.textAlign='right'; cx.fillText(Math.round(v),l-6,Y(v)+4); }
        for(k=0;k<=6;k++){ v=x0+(x1-x0)*k/6; cx.textAlign='center'; cx.fillText(dx?v.toFixed(dx):Math.round(v),X(v),H-b+16); }
        cx.fillStyle='#cbd5e1'; cx.textAlign='center'; cx.fillText(xl,(l+W-r)/2,H-6);
        cx.save(); cx.translate(13,(t+H-b)/2); cx.rotate(-Math.PI/2); cx.fillText(yl,0,0); cx.restore();
        return {X:X,Y:Y,l:l,r:r,t:t,b:b,W:W,H:H};
      }
      function rotulo(txt,x,y,col,al){ cx.fillStyle=col; cx.textAlign=al||'left'; cx.font='12px sans-serif'; cx.fillText(txt,x,y); cx.font='11px sans-serif'; }
      var pinta=function(){};

      if(modo==='hist'){
        var vr=box.getAttribute('data-var'), vals=[], etx;
        if(vr==='t'){ vals=T.slice(); etx='Temperatura ambiente (°C)'; }
        else if(vr==='p'){ vals=P.slice(); etx='Potencia (MW)'; }
        else { for(i=0;i<N;i++){ if(E[i]) vals.push(P[i]-(mo*T[i]+bo)); } etx='Residuo = real − predicho (MW)'; }
        var n=vals.length, so=vals.slice().sort(function(a,b){ return a-b; }), mn=so[0], mx=so[n-1], me=0, sd=0;
        vals.forEach(function(v){ me+=v; }); me/=n; vals.forEach(function(v){ sd+=(v-me)*(v-me); }); sd=Math.sqrt(sd/n);
        var med=(n%2)?so[(n-1)/2]:(so[n/2-1]+so[n/2])/2, dec=(mx-mn)>60?0:1;
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
          var lo=pmin-8, hi=pmax+8, L=lienzo(0.66), a=ejes(L,lo,hi,lo,hi,'Potencia predicha por la recta (MW)','Potencia real medida (MW)');
          for(i=0;i<xs.length;i++){ var ok=Math.abs(ys[i]-xs[i])<=tol; cx.globalAlpha=ok?0.25:0.7; cx.fillStyle=ok?'#38bdf8':'#fb7185';
            cx.beginPath(); cx.arc(a.X(xs[i]),a.Y(ys[i]),1.9,0,6.2832); cx.fill(); }
          cx.globalAlpha=1; cx.setLineDash([5,4]); cx.lineWidth=1.3; cx.strokeStyle='#fbbf24';
          [tol,-tol].forEach(function(d){ cx.beginPath(); cx.moveTo(a.X(lo),a.Y(lo+d)); cx.lineTo(a.X(hi),a.Y(hi+d)); cx.stroke(); });
          cx.setLineDash([8,5]); cx.lineWidth=2.4; cx.strokeStyle='#4ade80'; cx.beginPath(); cx.moveTo(a.X(lo),a.Y(lo)); cx.lineTo(a.X(hi),a.Y(hi)); cx.stroke(); cx.setLineDash([]);
          rotulo('predicción perfecta (real = predicho)',a.X(lo)+8,a.Y(lo+(hi-lo)*0.2)-4,'#4ade80');
          rotulo('rojo: error mayor que ±'+tol+' MW',a.X(hi)-8,a.Y(lo)-12,'#fb7185','right');
          K('k-r2',fmt(1-sse/sst,4)); K('k-rmse',fmt(Math.sqrt(sse/n),3)+' MW'); K('k-mae',fmt(sae/n,3)+' MW'); K('k-in',fmt(100*dentro/n,1)+' %');
          msg.textContent='El '+fmt(100*dentro/n,1)+' % de las predicciones queda a menos de '+tol+' MW del valor real.';
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
          var x=+sl.value; sv.textContent=fmt(x,1);
          var L=lienzo(0.62), xa=0, xz=45, a=ejes(L,xa,xz,380,520,'Temperatura ambiente (°C)','Potencia (MW)');
          cx.fillStyle='rgba(251,113,133,.10)';
          cx.fillRect(a.X(xa),a.t,a.X(tmin)-a.X(xa),a.Y(380)-a.t); cx.fillRect(a.X(tmax),a.t,a.X(xz)-a.X(tmax),a.Y(380)-a.t);
          rotulo('sin datos',a.X(xa)+6,a.t+14,'#fb7185'); rotulo('sin datos',a.X(xz)-6,a.t+14,'#fb7185','right');
          cx.globalAlpha=.16; cx.fillStyle='#38bdf8';
          for(i=0;i<N;i++){ if(E[i]) continue; cx.beginPath(); cx.arc(a.X(T[i]),a.Y(P[i]),1.7,0,6.2832); cx.fill(); }
          cx.globalAlpha=1; cx.beginPath();
          for(k=0;k<=45;k++){ var q=inter(k); if(k===0) cx.moveTo(a.X(k),a.Y(q.hi)); else cx.lineTo(a.X(k),a.Y(q.hi)); }
          for(k=45;k>=0;k--){ cx.lineTo(a.X(k),a.Y(inter(k).lo)); }
          cx.closePath(); cx.fillStyle='rgba(74,222,128,.17)'; cx.fill(); cx.setLineDash([5,4]); cx.strokeStyle='#4ade80'; cx.lineWidth=1.3; cx.stroke(); cx.setLineDash([]);
          cx.strokeStyle='#38bdf8'; cx.lineWidth=2.6; cx.beginPath(); cx.moveTo(a.X(xa),a.Y(mo*xa+bo)); cx.lineTo(a.X(xz),a.Y(mo*xz+bo)); cx.stroke();
          var q2=inter(x);
          cx.strokeStyle='rgba(230,237,247,.55)'; cx.setLineDash([3,4]); cx.lineWidth=1; cx.beginPath(); cx.moveTo(a.X(x),a.t); cx.lineTo(a.X(x),a.Y(380)); cx.stroke(); cx.setLineDash([]);
          cx.strokeStyle='#fbbf24'; cx.lineWidth=5; cx.lineCap='round'; cx.beginPath(); cx.moveTo(a.X(x),a.Y(q2.lo)); cx.lineTo(a.X(x),a.Y(q2.hi)); cx.stroke(); cx.lineCap='butt';
          cx.fillStyle='#fff'; cx.strokeStyle='#04121f'; cx.lineWidth=2; cx.beginPath(); cx.arc(a.X(x),a.Y(q2.h),6,0,6.2832); cx.fill(); cx.stroke();
          var dentro=(x>=tmin&&x<=tmax);
          K('k-h',fmt(q2.h,1)+' MW'); K('k-lo',fmt(q2.lo,1)+' MW'); K('k-hi',fmt(q2.hi,1)+' MW'); K('k-es',dentro?'Dentro ✓':'Fuera ⚠');
          var es=$('.k-es',box); if(es) es.style.color=dentro?'#4ade80':'#fb7185';
          msg.textContent=dentro?('A '+fmt(x,1)+' °C esperamos '+fmt(q2.h,1)+' MW; el 95 % de las veces la potencia real quedará entre '+fmt(q2.lo,1)+' y '+fmt(q2.hi,1)+' MW.')
            :('⚠ A '+fmt(x,1)+' °C no hay datos reales (solo de '+fmt(tmin,1)+' a '+fmt(tmax,1)+' °C). La recta da '+fmt(q2.h,1)+' MW, pero es una extrapolación: no te fíes.');
        };
        sl.addEventListener('input',pinta);
      }

      else if(modo==='anatomia'){
        K('k-m',fmt(mo,4)+' MW/°C'); K('k-b',fmt(bo,2)+' MW');
        pinta=function(){
          var d=+sl.value; sv.textContent=d;
          var L=lienzo(0.62), a=ejes(L,0,40,400,505,'Temperatura ambiente (°C)','Potencia (MW)');
          cx.globalAlpha=.16; cx.fillStyle='#38bdf8';
          for(i=0;i<N;i++){ cx.beginPath(); cx.arc(a.X(T[i]),a.Y(P[i]),1.7,0,6.2832); cx.fill(); }
          cx.globalAlpha=1; cx.strokeStyle='#38bdf8'; cx.lineWidth=3; cx.beginPath(); cx.moveTo(a.X(0),a.Y(bo)); cx.lineTo(a.X(40),a.Y(mo*40+bo)); cx.stroke();
          cx.fillStyle='#fb7185'; cx.beginPath(); cx.arc(a.X(0),a.Y(bo),6,0,6.2832); cx.fill();
          rotulo('b = '+fmt(bo,1)+' MW  (la recta, a 0 °C)',a.X(0)+10,a.Y(bo)-10,'#fb7185');
          var x1=15, y1=mo*x1+bo, x2=x1+d, y2=mo*x2+bo;
          cx.fillStyle='rgba(251,191,36,.18)'; cx.strokeStyle='#fbbf24'; cx.lineWidth=2; cx.setLineDash([5,4]);
          cx.beginPath(); cx.moveTo(a.X(x1),a.Y(y1)); cx.lineTo(a.X(x2),a.Y(y1)); cx.lineTo(a.X(x2),a.Y(y2)); cx.closePath(); cx.fill(); cx.stroke(); cx.setLineDash([]);
          rotulo('+'+d+' °C',(a.X(x1)+a.X(x2))/2,a.Y(y1)-8,'#fbbf24','center');
          rotulo(fmt(mo*d,1)+' MW',a.X(x2)+8,(a.Y(y1)+a.Y(y2))/2+4,'#fbbf24');
          K('k-d',fmt(mo*d,2)+' MW');
          msg.textContent='Si la temperatura sube '+d+' °C, la potencia estimada cambia '+fmt(mo*d,2)+' MW (pendiente × '+d+').';
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
"""


# ----------------------------------------------------------------- utilidades
def limpiar_texto(s):
    s = html.unescape(s or "")
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def esc(s):
    return html.escape(s or "", quote=True)


def a_local(iso):
    return dt_iso(iso).astimezone(ZONA)


def fecha_corta(dt):
    return f"{dt.day} {MESES_CORTOS[dt.month - 1]} {dt.year}"


def fecha_larga(dt):
    return f"{DIAS[dt.weekday()].capitalize()} {dt.day} de {MESES[dt.month - 1]} de {dt.year}"


def id_articulo(enlace):
    return hashlib.sha1(enlace.encode("utf-8")).hexdigest()[:16]


def fecha_entrada(entrada, ahora):
    for clave in ("published_parsed", "updated_parsed", "created_parsed"):
        t = entrada.get(clave)
        if t:
            try:
                dt = datetime(*t[:6], tzinfo=timezone.utc)
                return ahora if dt > ahora + timedelta(days=1) else dt
            except Exception:
                continue
    return ahora


def enlace_seguro(u):
    """Solo http(s) o rutas relativas simples; evita enlaces tipo javascript:."""
    u = (u or "").strip()
    return u if re.match(r"^(https?://\S+|[\w./#-]+)$", u) else ""


# ----------------------------------------------------------------- relevancia y temas
def compilar(palabras):
    partes = []
    for p in palabras or []:
        p = p.strip().lower()
        if not p:
            continue
        fin = r"\b" if len(p) <= 3 else ""
        partes.append(r"\b" + re.escape(p) + fin)
    return re.compile("|".join(partes), re.IGNORECASE) if partes else None


def preparar_patrones(config):
    return {
        "relevancia": compilar(config.get("relevancia", [])),
        "reglas": [(r["tema"], compilar(r.get("palabras", [])))
                   for r in config.get("clasificacion", [])],
    }


def es_relevante(patrones, texto):
    p = patrones["relevancia"]
    return True if p is None else bool(p.search(texto))


def clasificar(texto, patrones, temas):
    for tema, pat in patrones["reglas"]:
        if tema in temas and pat and pat.search(texto):
            return tema
    return "ia" if "ia" in temas else next(iter(temas))


def dt_iso(iso):
    """Fecha ISO → datetime con zona horaria (si venía sin zona, se toma como UTC)."""
    d = datetime.fromisoformat(iso)
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


# ----------------------------------------------------------------- titulares repetidos
STOP_SIM = {"the", "and", "for", "with", "from", "that", "this", "into", "how", "new", "will",
            "una", "uno", "los", "las", "del", "que", "con", "para", "por", "sus", "como", "mas",
            "sobre", "este", "esta", "ante", "tras", "hay", "est", "are", "has", "have", "can"}


def _tokens(texto):
    t = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().lower()
    return {w for w in re.findall(r"[a-z0-9]{3,}", t) if w not in STOP_SIM}


def agrupar_similares(articulos, umbral=0.5, horas=72):
    """Une titulares casi iguales de medios distintos. Recibe la lista ordenada de más
    nueva a más antigua; conserva el más reciente y anota en '_tambien' los otros medios."""
    kept, toks = [], []
    for a in articulos:
        t = _tokens(a.get("titulo_es") or a["titulo"]) | _tokens(a["titulo"])
        f = dt_iso(a["fecha"])
        dup = None
        if len(t) >= 3:
            for k, tk in zip(reversed(kept), reversed(toks)):
                if (dt_iso(k["fecha"]) - f).total_seconds() > horas * 3600:
                    break
                union = len(t | tk)
                if union and len(t & tk) / union >= umbral:
                    dup = k
                    break
        if dup is None:
            kept.append(a)
            toks.append(t)
        elif a["fuente"] != dup["fuente"]:
            otros = dup.setdefault("_tambien", [])
            if all(o["fuente"] != a["fuente"] for o in otros):
                otros.append({"fuente": a["fuente"], "enlace": a["enlace"]})
    return kept


def limitar_por_fuente_dia(items, maximo):
    cuenta, salida = defaultdict(int), []
    for a in items:
        clave = (a["fuente"], a["_dt"].date())
        if cuenta[clave] >= maximo:
            continue
        cuenta[clave] += 1
        salida.append(a)
    return salida


# ----------------------------------------------------------------- resúmenes semanales
def parsear_fecha(txt):
    return datetime.strptime(txt, "%Y-%m-%d")


def rango_semana(desde, hasta):
    d, h = parsear_fecha(desde), parsear_fecha(hasta)
    if d.year == h.year and d.month == h.month:
        return f"{d.day} al {h.day} de {MESES[h.month - 1]} de {h.year}"
    if d.year == h.year:
        return f"{d.day} de {MESES[d.month - 1]} al {h.day} de {MESES[h.month - 1]} de {h.year}"
    return (f"{d.day} de {MESES[d.month - 1]} de {d.year} al "
            f"{h.day} de {MESES[h.month - 1]} de {h.year}")


def cargar_resumenes(carpeta):
    """Lee data/resumenes/*.json (uno por semana). Ignora los mal formados."""
    resumenes = []
    if not carpeta.exists():
        return resumenes
    for f in sorted(carpeta.glob("*.json")):
        try:
            with open(f, encoding="utf-8") as fh:
                datos = json.load(fh)
            parsear_fecha(datos["desde"])
            parsear_fecha(datos["hasta"])
            if not isinstance(datos.get("temas"), dict):
                raise ValueError("falta el bloque 'temas'")
            resumenes.append(datos)
        except Exception as e:
            print(f"  [AVISO] Resumen {f.name} ignorado: {e}")
    resumenes.sort(key=lambda r: r["desde"], reverse=True)
    return resumenes


# ----------------------------------------------------------------- datos
def cargar_json(ruta, defecto):
    if ruta.exists():
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    return defecto


def guardar_datos(ruta, articulos):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    articulos = sorted(articulos, key=lambda a: a["fecha"], reverse=True)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("[\n")
        f.write(",\n".join(json.dumps(a, ensure_ascii=False, separators=(",", ":"))
                           for a in articulos))
        f.write("\n]\n")


def descargar(config, articulos, patrones):
    import feedparser  # solo hace falta para descargar; el resto del script no lo usa

    socket.setdefaulttimeout(25)
    ahora = datetime.now(timezone.utc)
    temas = config["temas"]
    conocidos = {a["id"] for a in articulos}
    nuevos_total = descartados_total = 0
    fallos = []

    for feed in config["feeds"]:
        nombre, url, tema_feed = feed["nombre"], feed["url"], feed["tema"]
        filtrar = bool(feed.get("filtrar"))
        maximo = feed.get("max", MAX_POR_FEED_DEFECTO)
        try:
            datos = feedparser.parse(url, agent=USER_AGENT)
        except Exception as e:
            fallos.append(nombre)
            print(f"  [ERROR] {nombre}: {e}")
            continue

        if not datos.entries:
            fallos.append(nombre)
            motivo = getattr(datos, "bozo_exception", "sin entradas")
            print(f"  [AVISO] {nombre}: sin entradas ({motivo})")
            continue

        nuevos = descartados = 0
        for e in datos.entries[:maximo]:
            enlace = (e.get("link") or "").strip()
            titulo = limpiar_texto(e.get("title"))
            if not enlace or not titulo:
                continue
            ident = id_articulo(enlace)
            if ident in conocidos:
                continue
            extracto = limpiar_texto(e.get("summary") or e.get("description"))[:RESUMEN_MAX]
            texto = f"{titulo} {extracto}"
            if filtrar and not es_relevante(patrones, texto):
                descartados += 1
                continue
            conocidos.add(ident)
            tema = tema_feed if tema_feed in temas else clasificar(texto, patrones, temas)
            art = {
                "id": ident,
                "titulo": titulo,
                "enlace": enlace,
                "fuente": nombre,
                "tema": tema,
                "fecha": fecha_entrada(e, ahora).isoformat(),
            }
            if filtrar:
                art["rel"] = True
            articulos.append(art)
            nuevos += 1
        nuevos_total += nuevos
        descartados_total += descartados
        print(f"  [OK] {nombre}: {nuevos} nuevos, {descartados} descartados por no ser relevantes")

    print(f"Total nuevos: {nuevos_total}. Descartados: {descartados_total}. "
          f"Feeds con problemas: {len(fallos)}")
    if fallos:
        print("  -> " + ", ".join(fallos))
    return articulos


def depurar(articulos, config, patrones):
    """Aplica las reglas actuales a lo ya guardado: quita lo irrelevante y recoloca
    lo que está en temas que ya no existen. Es idempotente."""
    temas = config["temas"]
    feeds = {f["nombre"]: f for f in config["feeds"]}
    limpios, quitados = [], 0
    for a in articulos:
        f = feeds.get(a["fuente"])
        filtrar = True if f is None else bool(f.get("filtrar"))
        tema_feed = f["tema"] if f and f["tema"] in temas else None
        if filtrar and not a.get("rel"):
            if not es_relevante(patrones, a["titulo"]):
                quitados += 1
                continue
            a["rel"] = True
            a["tema"] = tema_feed or clasificar(a["titulo"], patrones, temas)
        if f and f.get("tema") == "auto":
            a["tema"] = clasificar(a["titulo"], patrones, temas)
        elif a["tema"] not in temas:
            a["tema"] = tema_feed or clasificar(a["titulo"], patrones, temas)
        limpios.append(a)
    if quitados:
        print(f"Depuración: {quitados} titulares antiguos quitados por no ser relevantes.")
    return limpios


# ----------------------------------------------------------------- traducción
PALABRAS_ES = {"el", "la", "los", "las", "de", "del", "que", "en", "y", "con", "para", "por",
               "una", "un", "se", "su", "al", "lo", "más", "como", "es", "sobre", "este", "esta",
               "sus", "entre", "ya", "hay", "tras", "ante"}
MAX_TRADUCCIONES = 400  # por ejecución


def es_castellano(texto):
    palabras = re.findall(r"[a-záéíóúüñ]+", texto.lower())
    if not palabras:
        return False
    aciertos = sum(1 for p in palabras if p in PALABRAS_ES)
    return aciertos >= 2 and aciertos / len(palabras) >= 0.15


def _traduccion_en_es(traduccion):
    idiomas = traduccion.get_installed_languages()
    en = next((i for i in idiomas if i.code == "en"), None)
    es = next((i for i in idiomas if i.code == "es"), None)
    return en.get_translation(es) if en and es else None


def crear_traductor():
    """Traductor offline inglés→castellano con Argos Translate (gratuito).
    Devuelve una función texto→texto, o None si no está disponible."""
    try:
        import argostranslate.package as paquete
        import argostranslate.translate as traduccion

        tr = _traduccion_en_es(traduccion)
        if tr is None:
            print("  Descargando el modelo de traducción inglés→castellano…")
            paquete.update_package_index()
            pk = next((p for p in paquete.get_available_packages()
                       if p.from_code == "en" and p.to_code == "es"), None)
            if pk is None:
                raise RuntimeError("no hay paquete en→es en el índice")
            paquete.install_from_path(pk.download())
            tr = _traduccion_en_es(traduccion)
        if tr is None:
            raise RuntimeError("el modelo en→es no quedó disponible tras instalarlo")
        return tr.translate
    except Exception as e:
        print(f"  [AVISO] Traducción no disponible: {e}")
        return None


def necesita_traduccion(a, feeds):
    if a.get("titulo_es") or a.get("idioma") == "es":
        return False
    f = feeds.get(a["fuente"])
    if (f and f.get("idioma") == "es") or es_castellano(a["titulo"]):
        a["idioma"] = "es"
        return False
    return True


def traducir_titulares(articulos, config, traductor=None):
    """Añade 'titulo_es' a los titulares que no están en castellano. El original se conserva."""
    feeds = {f["nombre"]: f for f in config["feeds"]}
    pendientes = [a for a in articulos if necesita_traduccion(a, feeds)]
    if not pendientes:
        return 0
    pendientes.sort(key=lambda a: a["fecha"], reverse=True)
    pendientes = pendientes[:MAX_TRADUCCIONES]
    if traductor is None:
        traductor = crear_traductor()
    if traductor is None:
        print(f"  [AVISO] Sin traductor: {len(pendientes)} titulares quedan en su idioma original.")
        return 0
    hechos = errores = 0
    for a in pendientes:
        try:
            t = (traductor(a["titulo"]) or "").strip()
        except Exception as e:
            errores += 1
            print(f"  [AVISO] No se pudo traducir un titular: {e}")
            if errores >= 5:
                print("  [AVISO] Demasiados errores; se detiene la traducción en esta ejecución.")
                break
            continue
        if not t or t.lower() == a["titulo"].lower():
            a["idioma"] = "es"  # nombres propios u otro caso sin cambios: no reintentar
        else:
            a["titulo_es"] = t[:300]
        hechos += 1
    print(f"Titulares traducidos: {hechos}.")
    return hechos


# ----------------------------------------------------------------- borrador semanal
def escribir_borrador(articulos, config, ruta):
    """Escribe en 'ruta' (Markdown) los titulares de los últimos 7 días completos,
    agrupados por tema, listos para pegar en una conversación y redactar el resumen."""
    temas = config["temas"]
    hoy = datetime.now(ZONA).date()
    hasta = hoy - timedelta(days=1)
    desde = hasta - timedelta(days=6)
    d, h = desde.isoformat(), hasta.isoformat()
    semana = sorted((a for a in articulos if desde <= a_local(a["fecha"]).date() <= hasta),
                    key=lambda a: a["fecha"], reverse=True)
    dueno = os.environ.get("GITHUB_REPOSITORY_OWNER", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    aviso = f"@{dueno} " if dueno else ""
    enlace_subida = (f"https://github.com/{repo}/new/main?filename=data/resumenes/{d}.json"
                     if repo else f"data/resumenes/{d}.json")

    lineas = [
        f"{aviso}Borrador de la semana del {rango_semana(d, h)}: {len(semana)} titulares.",
        "",
        "**Cómo usarlo**",
        "1. Copia todo este mensaje en una conversación con Claude y escribe: "
        "«Redacta el resumen semanal por temas, en castellano y con enlaces a las fuentes».",
        "2. Revisa con calma lo que te devuelva.",
        f"3. Súbelo como `data/resumenes/{d}.json`: {enlace_subida}",
        "",
        "---",
    ]
    for clave, nombre in temas.items():
        propios = [a for a in semana if a["tema"] == clave]
        lineas += ["", f"## {nombre} ({len(propios)})"]
        if not propios:
            lineas.append("_Sin titulares esta semana._")
        for a in propios[:30]:
            titulo = (a.get("titulo_es") or a["titulo"]).replace("[", "(").replace("]", ")")
            lineas.append(f"- [{titulo}]({a['enlace']}) — {a['fuente']} · "
                          f"{a_local(a['fecha']).day} {MESES_CORTOS[a_local(a['fecha']).month - 1]}")
        if len(propios) > 30:
            lineas.append(f"- … y {len(propios) - 30} más.")
    plantilla = {"desde": d, "hasta": h,
                 "temas": {k: {"resumen": "", "fuentes": []} for k in temas}}
    lineas += ["", "---", "", "**Plantilla del archivo**", "```json",
               json.dumps(plantilla, ensure_ascii=False, indent=2), "```"]
    Path(ruta).write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"Borrador escrito en {ruta} con {len(semana)} titulares.")


# ----------------------------------------------------------------- sitio
class Sitio:
    def __init__(self, config, articulos, salida, resumenes=None):
        sitio = config["sitio"]
        self.cfg = config
        self.temas = config["temas"]
        self.descripciones = config.get("descripciones", {})
        self.titulo = sitio["titulo"]
        self.subtitulo = sitio.get("subtitulo", "")
        self.lema = sitio.get("lema", "")
        self.autor = sitio.get("autor", "")
        goat = (sitio.get("goatcounter") or "").strip().lower()
        self.goat = goat if re.fullmatch(r"[a-z0-9-]+", goat) else ""
        form = (sitio.get("formulario") or "").strip()
        self.formulario = form if form.startswith("https://") else ""
        self.articulos = sorted(articulos, key=lambda a: a["fecha"], reverse=True)
        for a in self.articulos:
            a.pop("_tambien", None)
        self.articulos = agrupar_similares(self.articulos)
        self.recursos = {}
        for r in config.get("recursos", []):
            if not re.fullmatch(r"[a-z0-9-]+", r.get("id", "")):
                continue
            ini, subs = 1, {}
            for sm in r.get("submodulos", []):
                subs[sm["n"]] = (ini, sm.get("paginas", 1))
                ini += sm.get("paginas", 1)
            for alt in [r.get("archivo", "")] + list(r.get("alternativos", [])):
                if self.localizar_recurso(alt):
                    r = dict(r, archivo=alt)
                    break
            if not self.localizar_recurso(r.get("archivo", "")):
                for carpeta in (RAIZ, RAIZ / "recursos"):
                    for f in sorted(carpeta.glob("*.pdf")) if carpeta.is_dir() else []:
                        norm = re.sub(r"[^a-z0-9]+", " ", unicodedata.normalize("NFKD", f.name.lower()).encode("ascii", "ignore").decode())
                        if ("modulo" in norm and "nivel" in norm) or ("regresion" in norm and ("modulo" in norm or "nivel" in norm or "lineal" in norm)):
                            r = dict(r, archivo=f.name)
                            break
            r = dict(r, _subs=subs, _total=ini - 1, _existe=self.localizar_recurso(r.get("archivo", "")) is not None)
            self.recursos[r["id"]] = r
        self.ayudas = cargar_json(RAIZ / "ayuda.json", {})
        if not isinstance(self.ayudas, dict):
            self.ayudas = {}
        self.proyectos = [p for p in config.get("proyectos", [])
                          if re.fullmatch(r"[a-z0-9-]+", p.get("id", ""))]
        self.resumenes = resumenes or []
        self.ultimo = self.resumenes[0] if self.resumenes else None
        self.salida = salida
        self.ahora = datetime.now(timezone.utc)
        for a in self.articulos:
            a["_dt"] = a_local(a["fecha"])

    # -- piezas comunes
    def color(self, tema):
        return COLORES.get(tema, "#94a3b8")

    def escribir(self, ruta_rel, contenido):
        ruta = self.salida / ruta_rel
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(contenido, encoding="utf-8")

    def pagina(self, titulo, cuerpo, raiz, activo="", buscador=False, descripcion=""):
        def act(k):
            return ' class="activo"' if k == activo else ""

        temas_html = "".join(
            f'<a href="{raiz}tema/{k}.html" style="--c:{self.color(k)}">'
            f'<span class="punto"></span>{esc(n)}</a>' for k, n in self.temas.items())
        desplegable_act = " activo" if (activo in self.temas or activo == "noticias") else ""
        enlaces = [
            f'<a href="{raiz}index.html"{act("portada")}>Portada</a>',
            f'<a href="{raiz}proyectos.html"{act("proyectos")}>Proyectos</a>',
            f'<a href="{raiz}retos.html"{act("retos")}>Retos de datos</a>',
            *([f'<a href="{raiz}biblioteca.html"{act("biblioteca")}>Biblioteca</a>'] if self.recursos else []),
            f'<details class="desplegable{desplegable_act}"><summary>Noticias</summary>'
            f'<div class="panel"><a href="{raiz}noticias.html">Todas las noticias</a>{temas_html}</div></details>',
            f'<a href="{raiz}resumenes.html"{act("resumenes")}>Resúmenes</a>',
            f'<a href="{raiz}archivo/index.html"{act("archivo")}>Archivo</a>',
            f'<a href="{raiz}sobre.html"{act("sobre")}>Sobre el proyecto</a>',
        ]
        if self.formulario:
            enlaces.append(f'<a href="{esc(self.formulario)}" target="_blank" '
                           f'rel="noopener noreferrer">Contacto</a>')
        menu = "".join(enlaces)

        caja = ('<div class="buscador"><input id="buscar" type="search" '
                'placeholder="Buscar en los titulares de esta página…" '
                'autocomplete="off"></div>') if buscador else ""
        partes = self.titulo.rsplit(" ", 1)
        marca = (f'{esc(partes[0])} <span>{esc(partes[1])}</span>'
                 if len(partes) == 2 else esc(self.titulo))
        n_guias = sum(1 for pp in self.proyectos if any(a.get("secciones") for a in (self.ayudas.get(pp["id"]) or {}).values() if isinstance(a, dict)))
        stats = ('<p class="stats-cab">'
                 f'<span><b>{len(self.proyectos)}</b> proyectos</span>'
                 f'<span><b>{n_guias}</b> con guía completa</span>'
                 f'<span><b>{len(self.articulos)}</b> noticias analizadas</span></p>')
        lema = f'<p class="lema">{esc(self.lema)}</p>' if self.lema else ""
        sub = f'<p class="subtitulo">{esc(self.subtitulo)}</p>' if self.subtitulo else ""
        autor = f'<p class="autor">por <b>{esc(self.autor)}</b></p>' if self.autor else ""
        ahora_l = self.ahora.astimezone(ZONA)
        actualizado = fecha_corta(ahora_l) + ahora_l.strftime(", %H:%M")
        autor_pie = f' · <span class="nombre">{esc(self.autor)}</span>' if self.autor else ""
        contacto = (f' · <a href="{esc(self.formulario)}" target="_blank" '
                    f'rel="noopener noreferrer">Enviar comentario</a>') if self.formulario else ""
        contador = (f'<script data-goatcounter="https://{self.goat}.goatcounter.com/count" '
                    f'async src="//gc.zgo.at/count.js"></script>') if self.goat else ""
        desc_meta = esc(descripcion or self.subtitulo)
        return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(titulo)} · {esc(self.titulo)}</title>
<meta name="description" content="{desc_meta}">
<meta name="theme-color" content="#0b1220">
<meta property="og:type" content="website">
<meta property="og:title" content="{esc(titulo)} · {esc(self.titulo)}">
<meta property="og:description" content="{desc_meta}">
<link rel="icon" href="{FAVICON}">
<link rel="stylesheet" href="{raiz}estilo.css">
</head><body>
<header class="sitio"><div class="contenedor"><div class="hero">
<a class="logo" href="{raiz}index.html" aria-label="{esc(self.titulo)}, inicio">{LOGO_SVG}</a>
<div><h1><a href="{raiz}index.html">{marca}</a></h1>{lema}{sub}{autor}{stats}</div>
</div></div></header>
<div class="barra"><div class="contenedor"><nav class="menu">{menu}</nav></div></div>
<main><div class="contenedor">
{caja}
{cuerpo}
</div></main>
<footer class="pie"><div class="contenedor">
{esc(self.titulo)}{autor_pie}{contacto}<br>
Actualizado automáticamente: {actualizado}. Titulares y enlaces a las fuentes originales, cuyo
contenido pertenece a cada medio. Los titulares en inglés se traducen automáticamente (el original
aparece al pasar el cursor). Los resúmenes semanales son elaboración propia.
Contenido divulgativo: no sustituye el consejo médico ni profesional.
</div></footer>
<script src="{raiz}interactivo.js" defer></script>
{contador}
</body></html>"""

    def item(self, a, con_fecha=True, con_tema=False):
        nuevo = ""
        if self.ahora - dt_iso(a["fecha"]) < timedelta(hours=48):
            nuevo = '<span class="nuevo">nuevo</span>'
        partes = []
        if con_tema:
            partes.append(f'<span class="etiqueta" style="--c:{self.color(a["tema"])}">'
                          f'{esc(self.temas.get(a["tema"], a["tema"]))}</span>')
        partes.append(esc(a["fuente"]))
        if con_fecha:
            partes.append(f'<time datetime="{esc(a["fecha"])}" data-iso="{esc(a["fecha"])}">'
                          f'{fecha_corta(a["_dt"])}</time>')
        meta = " · ".join(partes)
        titulo_es = a.get("titulo_es")
        texto_titulo = titulo_es or a["titulo"]
        pista = f' title="Original: {esc(a["titulo"])}"' if titulo_es else ""
        tambien = ""
        otros = [o for o in a.get("_tambien", []) if o["enlace"].startswith(("http://", "https://"))]
        if otros:
            tambien = ('<span class="tambien">También en: ' + ", ".join(
                f'<a href="{esc(o["enlace"])}" target="_blank" rel="noopener noreferrer">'
                f'{esc(o["fuente"])}</a>' for o in otros[:3]) + "</span>")
        ts = int(dt_iso(a["fecha"]).timestamp())
        return (f'<li class="item" data-tema="{esc(a["tema"])}" data-ts="{ts}" '
                f'style="--c:{self.color(a["tema"])}">'
                f'<a class="titular" href="{esc(a["enlace"])}" target="_blank" '
                f'rel="noopener noreferrer"{pista}>{esc(texto_titulo)}</a>'
                f'<span class="meta">{meta}{nuevo}</span>{tambien}</li>')

    def lista_por_dias(self, items):
        por_dia = defaultdict(list)
        for a in items:
            por_dia[a["_dt"].date()].append(a)
        salida = []
        for dia in sorted(por_dia, reverse=True):
            dt = datetime(dia.year, dia.month, dia.day)
            salida.append(f"<h3>{fecha_larga(dt)}</h3><ul class=\"lista\">"
                          + "".join(self.item(a, con_fecha=False) for a in por_dia[dia])
                          + "</ul>")
        return "".join(salida) or '<p class="vacio">Sin noticias.</p>'

    def chips_fuentes(self, fuentes):
        chips = []
        for f in (fuentes or [])[:4]:
            enlace = (f.get("enlace") or "").strip()
            nombre = f.get("fuente") or f.get("titulo") or "Fuente"
            if enlace.startswith(("http://", "https://")):
                chips.append(f'<a href="{esc(enlace)}" target="_blank" '
                             f'rel="noopener noreferrer">{esc(nombre)} ↗</a>')
        if not chips:
            return ""
        return '<div class="fuentes"><span>Fuentes:</span>' + "".join(chips) + "</div>"

    def resumen_de(self, clave, resumen_semana=None):
        r = resumen_semana or self.ultimo or {}
        t = (r.get("temas") or {}).get(clave) or {}
        return (t.get("resumen") or "").strip(), t.get("fuentes") or []

    # -- portada
    def conteo_semana(self, clave, dias):
        limite = self.ahora - timedelta(days=dias)
        return sum(1 for a in self.articulos if a["tema"] == clave
                   and dt_iso(a["fecha"]) >= limite)

    def seleccion_portada(self, propios, dias, maximo, max_fuente):
        limite = self.ahora - timedelta(days=dias)
        elegidos, por_fuente = [], defaultdict(int)
        for a in propios:
            if dt_iso(a["fecha"]) < limite:
                break
            if por_fuente[a["fuente"]] >= max_fuente:
                continue
            elegidos.append(a)
            por_fuente[a["fuente"]] += 1
            if len(elegidos) >= maximo:
                break
        if len(elegidos) < 3:
            for a in propios:
                if a not in elegidos:
                    elegidos.append(a)
                if len(elegidos) >= 3:
                    break
        return elegidos

    def tarjeta_tema(self, clave, nombre, dias):
        n = self.conteo_semana(clave, dias)
        texto, fuentes = self.resumen_de(clave)
        if texto:
            cuerpo = f'<p class="resumen">{esc(texto)}</p>' + self.chips_fuentes(fuentes)
        else:
            cuerpo = ('<p class="nota">Resumen semanal en preparación. '
                      'Pulsa para ver los titulares de este tema.</p>')
        return (f'<section class="tema-card bloque" id="{clave}" style="--c:{self.color(clave)}">'
                f'<a class="enlace-tema" href="tema/{clave}.html" '
                f'aria-label="Todas las noticias de {esc(nombre)}"></a>'
                f'<header><span class="punto"></span><h2>{esc(nombre)}</h2>'
                f'<span class="cuenta">{n} esta semana</span></header>'
                f'{cuerpo}<span class="mas">Ver las noticias →</span></section>')

    NIVEL_TXT = {"basico": "básico", "medio": "medio", "avanzado": "avanzado", "experto": "experto"}
    BLOQUES = (("regresion", "#38bdf8", "Regresión", "predecir un número"),
               ("clasificacion", "#fbbf24", "Clasificación", "decidir a qué grupo pertenece algo"),
               ("redes", "#c084fc", "Redes neuronales", "aprendizaje profundo"))

    NIVEL_DESC = {"basico": "Para empezar desde cero.",
                  "medio": "Un paso más: más variables y más modelos.",
                  "avanzado": "Técnicas más potentes y datos más difíciles."}
    NIVEL_COLOR = {"basico": "#4ade80", "medio": "#fbbf24", "avanzado": "#fb7185"}

    def categorias(self):
        return list(self.BLOQUES) + [("experto", "#fb7185", "Experto",
                                      "proyectos de toda índole, para cuando domines lo anterior")]

    def de_bloque(self, b, nv=None):
        return [p for p in self.proyectos if p.get("bloque") == b and (nv is None or p.get("nivel") == nv)]

    def cat_card(self, href, color, titulo, sub, n, items=None):
        lista = ('<ul class="mini">' + "".join(f"<li>{esc(t)}</li>" for t in items) + "</ul>") if items else ""
        return (f'<section class="tema-card" style="--c:{color}">'
                f'<a class="enlace-tema" href="{href}" aria-label="{esc(titulo)}"></a>'
                f'<header><span class="punto"></span><h2>{esc(titulo)}</h2>'
                f'<span class="cuenta">{n} proyectos</span></header>'
                f'<p class="resumen">{esc(sub[:1].upper() + sub[1:])}</p>{lista}'
                f'<span class="mas">Ver →</span></section>')

    def caja_ayuda_pdf(self, clave_nivel):
        for r in self.recursos.values():
            if r.get("ayuda_nivel") == clave_nivel:
                if r["_existe"]:
                    href = "../recursos/" + quote(r["archivo"])
                    txt = "Descargar PDF ↓"
                    extra = ' download'
                else:
                    href = "../biblioteca.html"
                    txt = "Ver en la Biblioteca →"
                    extra = ""
                return (f'<div class="btn-ayuda"><span style="font-size:1.6rem">📘</span><div><b>Ayuda: {esc(r["titulo"])}</b>'
                        f'<small>Apuntes en PDF para estudiar y consultar mientras haces los proyectos de este nivel.</small></div>'
                        f'<a href="{href}"{extra}>{txt}</a></div>')
        return ""

    def categorias_html(self, carpeta):
        out = []
        for clave, color, nombre, sub in self.categorias():
            ps = self.de_bloque(clave)
            if ps:
                out.append(self.cat_card(f"{carpeta}{clave}.html", color, nombre, sub, len(ps)))
        return f'<div class="cats">{"".join(out)}</div>'

    def paginas_bloques(self):
        for clave, color, nombre, sub in self.categorias():
            ps = self.de_bloque(clave)
            if not ps:
                continue
            if clave == "experto":
                cuerpo = ('<p class="migas"><a href="../proyectos.html">← Proyectos</a></p>'
                          f'<h2 style="--c:{color}">{esc(nombre)}<small>{esc(sub)}</small></h2>'
                          + f'<p class="intro-bloque">{esc(self.cfg.get("intros", {}).get(clave, ""))}</p>'
                          + '<div class="tarjetas">'
                          + "".join(self.tarjeta_proyecto(p, "") for p in ps) + "</div>")
                self.escribir(f"proyectos/{clave}.html", self.pagina(nombre, cuerpo, "../", "proyectos"))
                continue
            cards = []
            for nv in ("basico", "medio", "avanzado"):
                pn = self.de_bloque(clave, nv)
                if not pn:
                    continue
                cards.append(self.cat_card(f"{clave}-{nv}.html", self.NIVEL_COLOR[nv],
                                           f"Nivel {self.NIVEL_TXT[nv]}", self.NIVEL_DESC[nv],
                                           len(pn), [p["titulo"] + (" · ⏱ " + p["tiempo"] if p.get("tiempo") else "") for p in pn]))
                cuerpo = ('<p class="migas"><a href="' + f'{clave}.html">← {esc(nombre)}</a></p>'
                          f'<h2 style="--c:{self.NIVEL_COLOR[nv]}">{esc(nombre)} · nivel {self.NIVEL_TXT[nv]}'
                          f'<small>{esc(self.NIVEL_DESC[nv])}</small></h2>'
                          + f'<p class="intro-bloque">{esc(self.cfg.get("intros", {}).get(clave, ""))}</p>'
                          + self.caja_ayuda_pdf(f"{clave}-{nv}")
                          + self.caja_aprenderas(self.cfg.get("aprenderas", {}).get(f"{clave}-{nv}"), "nivel")
                          + '<div class="tarjetas">'
                          + "".join(self.tarjeta_proyecto(p, "") for p in pn) + "</div>")
                self.escribir(f"proyectos/{clave}-{nv}.html",
                              self.pagina(f"{nombre}, nivel {self.NIVEL_TXT[nv]}", cuerpo, "../", "proyectos"))
            cuerpo = ('<p class="migas"><a href="../proyectos.html">← Proyectos</a></p>'
                      f'<h2 style="--c:{color}">{esc(nombre)}<small>{esc(sub)}</small></h2>'
                      f'<p class="intro-bloque">{esc(self.cfg.get("intros", {}).get(clave, ""))}</p>'
                      '<p class="desc">Elige un nivel.</p>'
                      f'<div class="cats">{"".join(cards)}</div>')
            self.escribir(f"proyectos/{clave}.html", self.pagina(nombre, cuerpo, "../", "proyectos"))

    def portada(self):
        sitio = self.cfg["sitio"]
        dias = sitio.get("dias_portada", 7)
        tarjetas = "".join(self.tarjeta_tema(k, n, dias) for k, n in self.temas.items())
        if self.ultimo:
            semana = f'Semana del {rango_semana(self.ultimo["desde"], self.ultimo["hasta"])}'
        else:
            semana = "Resumen semanal"
        p1 = self.proyectos[0] if self.proyectos else None
        hero = ""
        if p1:
            hero = ('<section class="hero"><div><span class="etq">Aprende haciendo</span>'
                    '<h2 class="hero-t">De tu taller a tus datos, paso a paso</h2>'
                    '<p class="sub">Inteligencia artificial, robótica y automatización explicadas desde cero, con datos reales y abiertos. '
                    'Cada proyecto es una secuencia de pasos pequeños: explicación, código en Colab, gráficos y un test.</p>'
                    '<div class="chips2"><span class="chip2" style="color:#4ade80;border-color:#4ade8077">32 proyectos</span>'
                    '<span class="chip2" style="color:#38bdf8;border-color:#38bdf877">Regresión · Clasificación · Redes</span>'
                    '<span class="chip2" style="color:#fbbf24;border-color:#fbbf2477">Gratis y en castellano</span></div>'
                    f'<a class="cta" href="proyectos/{esc(p1["id"])}.html">Empieza aquí: {esc(p1["titulo"])} · ⏱ {esc(p1.get("tiempo", ""))} →</a></div>'
                    f'<div class="flujo-h">{self.svg_flujo_hero(p1.get("flujo"))}</div></section>')
        cuerpo = (
            hero +
            '<h2 id="aprende" style="--c:#4ade80">Aprende haciendo'
            '<small>de la regresión simple a las redes convolucionales, con datos reales y abiertos. Elige una familia</small></h2>'
            + self.categorias_html("proyectos/")
            + f'<h2 id="resumen" style="--c:#818cf8">Noticias de la semana<small>{esc(semana)}. '
            'Pulsa un tema para ver sus noticias</small></h2>'
            f'<div class="rejilla">{tarjetas}</div>'
            '<p><a class="ver-todos" href="noticias.html">Todas las noticias, con buscador y filtros →</a></p>')
        self.escribir("index.html", self.pagina(
            "Portada", cuerpo, "", "portada",
            descripcion="Proyectos paso a paso y noticias de inteligencia artificial, robótica y automatización, en castellano."))

    def pagina_noticias(self):
        sitio = self.cfg["sitio"]
        max_flujo = sitio.get("max_flujo_noticias", 150)
        chips = ('<button class="chip-tema activo" data-tema="todas" type="button">Todas</button>'
                 + "".join(f'<button class="chip-tema" data-tema="{k}" type="button" '
                           f'style="--c:{self.color(k)}">{esc(n)}</button>'
                           for k, n in self.temas.items()))
        tiempo = ('<div class="chips tiempo"><button class="chip-tiempo activo" data-horas="0" type="button">Todo</button>'
                  '<button class="chip-tiempo" data-horas="24" type="button">Últimas 24 horas</button>'
                  '<button class="chip-tiempo" data-horas="168" type="button">Esta semana</button>'
                  '<button class="chip-tiempo" data-horas="720" type="button">Este mes</button></div>')
        flujo = limitar_por_fuente_dia(self.articulos, sitio.get("max_por_fuente_dia", 4))[:max_flujo]
        if flujo:
            lista = ('<ul class="lista flujo" id="flujo">'
                     + "".join(self.item(a, con_tema=True) for a in flujo) + "</ul>")
        else:
            lista = '<p class="vacio">Aún no hay noticias. Aparecerán tras la primera actualización.</p>'
        cuerpo = ('<h2 id="ultimas" style="--c:#38bdf8">Noticias<small>de todos los temas, de más nueva a más antigua</small></h2>'
                  '<div class="buscador"><input id="buscar" type="search" autocomplete="off" '
                  'placeholder="Buscar en las noticias… (pulsa / para buscar)"></div>'
                  f'<div class="chips">{chips}</div>{tiempo}{lista}'
                  '<p id="sin-resultados" class="vacio oculto">No hay noticias con ese filtro.</p>'
                  '<button id="mas" class="boton-mas oculto" type="button">Cargar más noticias</button>')
        self.escribir("noticias.html", self.pagina(
            "Noticias", cuerpo, "", "noticias",
            descripcion="Noticias de inteligencia artificial, robótica y automatización."))

    # -- temas
    def paginas_tema(self):
        for clave, nombre in self.temas.items():
            propios = [a for a in self.articulos if a["tema"] == clave]
            por_mes = defaultdict(list)
            for a in propios:
                por_mes[(a["_dt"].year, a["_dt"].month)].append(a)
            partes = [f'<h2 style="--c:{self.color(clave)}">{esc(nombre)}'
                      f'<small>{len(propios)} titulares</small></h2>']
            if self.descripciones.get(clave):
                partes.append(f'<p class="desc">{esc(self.descripciones[clave])}</p>')
            texto, fuentes = self.resumen_de(clave)
            if texto:
                partes.append(
                    f'<section class="bloque-resumen" style="--c:{self.color(clave)}">'
                    f'<h4>Resumen · semana del '
                    f'{rango_semana(self.ultimo["desde"], self.ultimo["hasta"])}</h4>'
                    f'<p>{esc(texto)}</p>{self.chips_fuentes(fuentes)}</section>')
            if not propios:
                partes.append('<p class="vacio">Aún no hay noticias de este tema.</p>')
            for (y, m) in sorted(por_mes, reverse=True):
                items = por_mes[(y, m)]
                partes.append(
                    f'<section class="bloque"><h3>{MESES[m - 1].capitalize()} {y} '
                    f'· <a href="../archivo/{y}/{m:02d}/{clave}.html">ver mes completo</a></h3>'
                    '<ul class="lista">' + "".join(self.item(a) for a in items[:30]) + "</ul>"
                    + (f'<p class="vacio">… y {len(items) - 30} más en el mes completo.</p>'
                       if len(items) > 30 else "") + "</section>")
            self.escribir(f"tema/{clave}.html",
                          self.pagina(nombre, "".join(partes), "../", clave, buscador=True,
                                      descripcion=self.descripciones.get(clave, "")))

    # -- resúmenes, proyectos, retos, acerca
    def pagina_resumenes(self):
        partes = ['<h2>Resúmenes semanales</h2>'
                  '<p class="desc">Cada semana, lo más importante de cada tema, en castellano y con enlaces '
                  'a las fuentes originales.</p>']
        if not self.resumenes:
            partes.append('<p class="vacio">Los resúmenes semanales aparecerán aquí, '
                          'del más nuevo al más antiguo.</p>')
        for r in self.resumenes:
            partes.append(f'<h3 class="semana">Semana del {rango_semana(r["desde"], r["hasta"])}</h3>')
            for clave, nombre in self.temas.items():
                texto, fuentes = self.resumen_de(clave, r)
                if not texto:
                    continue
                partes.append(
                    f'<section class="bloque-resumen" style="--c:{self.color(clave)}">'
                    f'<h4>{esc(nombre)}</h4><p>{esc(texto)}</p>{self.chips_fuentes(fuentes)}</section>')
        self.escribir("resumenes.html", self.pagina(
            "Resúmenes semanales", "".join(partes), "", "resumenes",
            descripcion="Resumen semanal por temas de inteligencia artificial, robótica y automatización."))

    ESTADOS = {"proximo": "Próximo", "idea": "Idea", "curso": "En curso", "publicado": "Publicado"}

    def etiquetas(self, p, compacta=False):
        nivel = (p.get("nivel") or "").strip().lower()
        area = (p.get("area") or "").strip()
        t = []
        if compacta:
            return (f'<div class="etiquetas"><span class="tag">{esc(p["tecnica"])}</span></div>'
                    if p.get("tecnica") else "")
        if nivel:
            t.append(f'<span class="tag nivel-{esc(nivel)}">Nivel: {esc(self.NIVEL_TXT.get(nivel, nivel))}</span>')
        if area:
            t.append(f'<span class="tag area">Área: {esc(area)}</span>')
        if p.get("tipo"):
            t.append(f'<span class="tag">Tipo: {esc(p["tipo"])}</span>')
        if p.get("tecnica"):
            t.append(f'<span class="tag">Técnica: {esc(p["tecnica"])}</span>')
        return f'<div class="etiquetas">{"".join(t)}</div>' if t else ""

    ICONO_AREA = {"energía": "⚡", "aeronáutica": "✈️", "ingeniería": "⚙️", "mantenimiento": "🔧", "robótica": "🤖",
                  "visión artificial": "👁️", "ia": "🧠"}

    def tarjeta_proyecto(self, p, base, compacta=False):
        est = p.get("estado", "idea")
        n = self.proyectos.index(p) + 1
        clase = " compacta" if compacta else ""
        nivel = (p.get("nivel") or "").strip().lower()
        col = self.NIVEL_COLOR.get(nivel, "#38bdf8")
        icono = self.ICONO_AREA.get((p.get("area") or "").strip().lower(), "🧠")
        tiempo = (f'<span class="tiempo" title="Tiempo estimado">⏱ {esc(p["tiempo"])}</span>' if p.get("tiempo") else "")
        return (f'<article class="proyecto{clase}" style="--nv:{col}"><div class="cabecera-card">'
                f'<span class="icono-card">{icono}</span><span class="num">Proyecto {n}</span>'
                f'<span class="estado {esc(est)}">{esc(self.ESTADOS.get(est, est))}</span></div>'
                f'<h3>{esc(p.get("titulo", ""))}</h3>'
                f'{self.etiquetas(p, compacta)}<p>{esc(p.get("descripcion", ""))}</p>'
                f'<div class="pie-card">{tiempo}<a class="ir" href="{base}{esc(p["id"])}.html">Abrir proyecto →</a></div></article>')

    def pagina_proyectos(self):
        tarjetas = self.categorias_html("proyectos/")
        cuerpo = ('<h2 style="--c:#4ade80">Proyectos<small>aprende haciendo</small></h2>'
                  '<p class="desc">Programas útiles explicados paso a paso, con datos reales y abiertos. '
                  'Elige una familia y después un nivel. Cada proyecto tiene su ficha técnica y explica cada paso desde '
                  'cero (cómo, por qué y para qué) y recoge siempre las fuentes de los datos y los límites '
                  'del resultado.</p>'
                  + tarjetas)
        self.escribir("proyectos.html", self.pagina(
            "Proyectos", cuerpo, "", "proyectos",
            descripcion="Programas explicados paso a paso con datos reales y abiertos."))
        self.paginas_bloques()
        for p in self.proyectos:
            self.ficha_proyecto(p)

    def noticias_relacionadas(self, p, maximo=6):
        pat = compilar(p.get("noticias_palabras", []))
        if not pat:
            return []
        out = []
        for a in self.articulos:
            if pat.search((a.get("titulo_es") or "") + " " + a["titulo"]):
                out.append(a)
                if len(out) >= maximo:
                    break
        return out

    def ficha_proyecto(self, p):
        def fila(k, v):
            return f"<dt>{esc(k)}</dt><dd>{v}</dd>" if v else ""

        ds = p.get("dataset") or {}
        url = enlace_seguro(ds.get("url"))
        dataset = ""
        if ds.get("nombre"):
            dataset = esc(ds["nombre"])
            if url.startswith("http"):
                dataset += (f' · <a href="{esc(url)}" target="_blank" rel="noopener noreferrer">'
                            f'enlace oficial ↗</a>')
            if ds.get("verificado") is False:
                dataset += ' <span class="nota-dato">(conjunto y enlace por confirmar antes de empezar)</span>'
        herr = "".join(f'<span class="tag">{esc(h)}</span> ' for h in p.get("herramientas", []))
        est = p.get("estado", "idea")
        ficha = ('<dl class="ficha-tec">'
                 + fila("Nivel", esc(self.NIVEL_TXT.get((p.get("nivel") or "").lower(), p.get("nivel", ""))).capitalize())
                 + fila("Área", esc(p.get("area", "")).capitalize())
                 + fila("Tipo de problema", esc(p.get("tipo", "")))
                 + fila("Técnica", esc(p.get("tecnica", "")))
                 + fila("Dataset", dataset)
                 + fila("Objetivo", esc(p.get("objetivo", "")))
                 + fila("Datos usados", esc(p.get("datos", "")))
                 + fila("Herramientas", herr)
                 + fila("Método", esc(p.get("metodo", "")))
                 + fila("Métrica", esc(p.get("metrica", "")))
                 + "</dl>")
        pasos = []
        for num, st in enumerate(p.get("pasos", []), 1):
            partes = [f'<h4>{esc(st.get("titulo", ""))}<span class="hecho-marca">✓ completado</span></h4>']
            for clave, etiqueta in (("que", "Qué hacemos"), ("como", "Cómo"),
                                    ("porque", "Por qué"), ("para", "Para qué")):
                if st.get(clave):
                    partes.append(f"<p><b>{etiqueta}:</b> {esc(st[clave])}</p>")
            if self.ayuda_paso(p["id"], num):
                etiqueta = ("Abrir el paso: explicación, código, resultado y test →"
                            if self.ayuda_paso(p["id"], num).get("secciones")
                            else "Abrir el paso: ayuda del libro, test y entrega →")
                partes.append(f'<a class="enlace-paso" href="{esc(p["id"])}-paso-{num}.html">{etiqueta}</a>')
            else:
                partes.append(self.ayuda_html(st.get("ayuda"), "../"))
            pasos.append(f'<li id="paso-{num}" data-paso="{esc(p["id"])}:{num}">' + "".join(partes) + "</li>")
        if p.get("esquema") and not pasos:
            esquema = ('<p class="desc">Esquema previsto. Los pasos se explicarán uno a uno, desde cero, '
                       'cuando hagamos el proyecto.</p><ol class="esquema">'
                       + "".join(f"<li>{esc(t)}</li>" for t in p["esquema"]) + "</ol>")
        else:
            esquema = ""
        cod = enlace_seguro(p.get("codigo"))
        codigo = (f'<a class="btn-descarga" href="{esc(cod)}" target="_blank" rel="noopener noreferrer">▶ Abrir el código en Colab</a>'
                  if cod.startswith("http") else '<span class="vacio">Se publicará con el proyecto.</span>')
        entrega_items = []
        ent = p.get("entrega") or {}
        for clave, nombre in (("notebook", "Notebook"), ("repositorio", "Repositorio"),
                              ("demo", "Demo"), ("articulo", "Artículo")):
            u = enlace_seguro(ent.get(clave))
            if u.startswith("http"):
                entrega_items.append(f'<li><a href="{esc(u)}" target="_blank" '
                                     f'rel="noopener noreferrer">{nombre} ↗</a></li>')
            else:
                entrega_items.append(f'<li>{nombre}<span>pendiente</span></li>')
        contacto = (f' <a href="{esc(self.formulario)}" target="_blank" rel="noopener noreferrer">'
                    f'Escríbeme</a>.') if self.formulario else ""
        if p.get("bloque") in ("regresion", "clasificacion", "redes"):
            nom = {c: n for c, _, n, _ in self.BLOQUES}[p["bloque"]]
            migas = (f'<p class="migas"><a href="{p["bloque"]}-{p["nivel"]}.html">← {esc(nom)} · '
                     f'nivel {self.NIVEL_TXT.get(p["nivel"], p["nivel"])}</a></p>')
        elif p.get("bloque") == "experto":
            migas = '<p class="migas"><a href="experto.html">← Experto</a></p>'
        else:
            migas = '<p class="migas"><a href="../proyectos.html">← Todos los proyectos</a></p>'
        rel = self.noticias_relacionadas(p)
        noticias = ""
        if rel:
            noticias = ('<h2 style="--c:#38bdf8">Noticias relacionadas</h2><ul class="lista">'
                        + "".join(self.item(a, con_tema=True) for a in rel) + "</ul>")
        cuerpo = (
            migas +
            self.hero_proyecto(p, len(p.get("pasos", [])))
            + self.resultado_final(p)
            + self.caja_aprenderas(p.get("aprenderas") or self.cfg.get("aprenderas", {}).get(
                f'{p.get("bloque")}-{p.get("nivel")}'))
            + '<h2 style="--c:#38bdf8">Ficha técnica</h2>' + ficha
            + '<h2 style="--c:#fbbf24">Métrica y pasos del proyecto'
              '<small>explicados desde cero</small></h2>'
            + (f'<p class="desc">Medimos el resultado con: {esc(p.get("metrica", ""))}</p>'
               if p.get("metrica") else "")
            + ('<p class="prog"><span class="prog-barra"><i></i></span>'
               f'<span><b class="prog-n">0</b> de {len(pasos)} pasos completados (se guarda en este navegador)</span></p>'
               if pasos else "")
            + self.red_progreso(p["id"], [st.get("titulo", "") for st in p.get("pasos", [])])
            + (f'<ol class="pasos">{"".join(pasos)}</ol>' if pasos else esquema)
            + '<h2 style="--c:#4ade80">Resultados</h2>'
            + self.resultado_final(p, "El resultado final de este proyecto", "Resultado final")
            + self.graficos_resultado(p)
            + f'<p>{esc(p.get("resultados") or "Este proyecto aún no está completado: aquí aparecerán la gráfica final, la ecuación, el R² y la conclusión.")}</p>'
            + '<h2 style="--c:#fb7185">Limitaciones</h2>'
            + f'<p>{esc(p.get("limitaciones") or "Se explicarán al completar el proyecto: qué no cubre el modelo y en qué casos no conviene fiarse de él.")}</p>'
            + '<h2 style="--c:#818cf8">Código</h2>' + f"<p>{codigo}</p>"
            + f'<p class="desc">¿Has encontrado un error o tienes una mejora? Será bienvenida.{contacto}</p>'
            + noticias)
        self.escribir(f"proyectos/{p['id']}.html", self.pagina(
            p.get("titulo", ""), cuerpo, "../", "proyectos", descripcion=p.get("descripcion", "")))

    def pagina_retos(self):
        tarjetas = []
        for r in self.cfg.get("retos", []):
            url = (r.get("url") or "").strip()
            if not url.startswith("https://"):
                continue
            marca = '<span class="estado">Para empezar</span>' if r.get("destacado") else ""
            tarjetas.append(
                f'<article class="proyecto">{marca}<h3>{esc(r.get("nombre", ""))}</h3>'
                f'<p>{esc(r.get("descripcion", ""))}</p>'
                f'<a class="ir" href="{esc(url)}" target="_blank" rel="noopener noreferrer">'
                f'Visitar ↗</a></article>')
        cuerpo = ('<h2>Retos de datos</h2>'
                  '<p class="desc">Plataformas con retos reales para practicar. Más adelante publicaré aquí '
                  'fichas de retos concretos: qué se pide, qué enfoques funcionaron y qué se aprende. '
                  'Siempre respetando las normas de cada plataforma y citando a sus autores.</p>'
                  f'<div class="tarjetas">{"".join(tarjetas)}</div>')
        self.escribir("retos.html", self.pagina(
            "Retos de datos", cuerpo, "", "retos",
            descripcion="Plataformas de retos de datos para aprender inteligencia artificial."))

    def sobre(self):
        sitio = self.cfg["sitio"]
        info = sitio.get("sobre") or {}
        textos = "".join(f"<p>{esc(t)}</p>" for t in (sitio.get("acerca") or []))
        fuentes = sorted({f["nombre"] for f in self.cfg.get("feeds", [])})
        reglas = "".join(f"<li><b>{esc(self.temas.get(r['tema'], r['tema']))}</b>: "
                         f"{esc(', '.join(r.get('palabras', [])[:6]))}…</li>"
                         for r in self.cfg.get("clasificacion", []) if r["tema"] in self.temas)
        no_hace = "".join(f"<li>{esc(t)}</li>" for t in info.get("no_hace", []))
        contacto = (f'<p>Puedes escribirme desde <a href="{esc(self.formulario)}" target="_blank" '
                    f'rel="noopener noreferrer">este formulario</a>; no se muestra ningún correo.</p>'
                    if self.formulario else
                    "<p>Próximamente habrá un formulario de contacto privado.</p>")
        cuerpo = (
            '<div class="sobre"><h2>Sobre el proyecto</h2>' + textos
            + (f"<h3>Qué es esta web</h3><p>{esc(info['que_es'])}</p>" if info.get("que_es") else "")
            + "<h3>Cómo se seleccionan las noticias</h3>"
              "<p>Cada día un programa lee los canales RSS de las fuentes y se queda solo con los "
              "titulares que tienen que ver con inteligencia artificial, robótica y automatización "
              "(según una lista de palabras clave). Las fuentes muy generales pasan además este filtro; "
              "las especializadas entran enteras. Los titulares casi idénticos de medios distintos se "
              "agrupan en uno, y en la portada se limita cuántos entran de cada medio al día.</p>"
              "<h3>Cómo se clasifican</h3><p>Por reglas de prioridad: se comprueba cada tema en este "
              "orden y gana el primero que encaja (si ninguno, va a Inteligencia artificial).</p>"
              f"<ul>{reglas}</ul>"
            + "<h3>Fuentes</h3><p>" + esc(" · ".join(fuentes)) + "</p>"
              "<p>Los titulares en inglés se traducen automáticamente al castellano; el original "
              "aparece al pasar el cursor. De cada noticia solo se muestra título, fuente, fecha y "
              "enlace: el contenido pertenece a cada medio.</p>"
              "<h3>Resúmenes semanales</h3><p>Los escribo y reviso yo cada semana, con enlaces a las "
              "fuentes.</p>"
            + (f"<h3>Qué no hace esta web</h3><ul>{no_hace}</ul>" if no_hace else "")
            + "<h3>Contacto</h3>" + contacto + "</div>")
        self.escribir("sobre.html", self.pagina(
            "Sobre el proyecto", cuerpo, "", "sobre",
            descripcion="Qué es esta web, cómo se eligen y clasifican las noticias y qué no hace."))

    # -- archivo
    def archivo(self):
        por_mes = defaultdict(list)
        for a in self.articulos:
            por_mes[(a["_dt"].year, a["_dt"].month)].append(a)

        años = sorted({y for y, _ in por_mes}, reverse=True)
        partes = ['<h2>Archivo por año y mes</h2>']
        if not años:
            partes.append('<p class="vacio">El archivo se irá llenando con el tiempo.</p>')
        for y in años:
            partes.append(f"<h3>{y}</h3><div class=\"fichas\">")
            for m in sorted((mm for yy, mm in por_mes if yy == y), reverse=True):
                partes.append(
                    f'<a class="ficha" href="{y}/{m:02d}/index.html">'
                    f'<b>{MESES[m - 1].capitalize()}</b>'
                    f'<span>{len(por_mes[(y, m)])} titulares</span></a>')
            partes.append("</div>")
        self.escribir("archivo/index.html",
                      self.pagina("Archivo", "".join(partes), "../", "archivo"))

        for (y, m), items in por_mes.items():
            carpeta = f"archivo/{y}/{m:02d}"
            raiz = "../../../"
            fichas = []
            for clave, nombre in self.temas.items():
                propios = [a for a in items if a["tema"] == clave]
                if not propios:
                    continue
                fichas.append(
                    f'<a class="ficha" style="--c:{self.color(clave)}" '
                    f'href="{clave}.html"><b>{esc(nombre)}</b>'
                    f'<span>{len(propios)} titulares</span></a>')
                cuerpo = (f'<h2 style="--c:{self.color(clave)}">{esc(nombre)} · '
                          f'{MESES[m - 1]} {y}</h2>'
                          f'<p><a href="index.html">← {MESES[m - 1].capitalize()} {y}</a></p>'
                          + self.lista_por_dias(propios))
                self.escribir(f"{carpeta}/{clave}.html",
                              self.pagina(f"{nombre} — {MESES[m - 1]} {y}", cuerpo,
                                          raiz, "archivo", buscador=True))
            cuerpo = (f'<h2>{MESES[m - 1].capitalize()} {y}'
                      f'<small>{len(items)} titulares</small></h2>'
                      f'<p><a href="../../index.html">← Todo el archivo</a></p>'
                      f'<div class="fichas">{"".join(fichas)}</div>'
                      '<h3>Todo el mes, por fecha</h3>'
                      + self.lista_por_dias(items))
            self.escribir(f"{carpeta}/index.html",
                          self.pagina(f"{MESES[m - 1].capitalize()} {y}", cuerpo, raiz,
                                      "archivo", buscador=True))

    @staticmethod
    def localizar_recurso(nombre):
        if not nombre or "/" in nombre or "\\" in nombre or not nombre.lower().endswith(".pdf"):
            return None
        for carpeta in (RAIZ, RAIZ / "recursos"):
            f = carpeta / nombre
            if f.is_file():
                return f
        return None

    def ayuda_html(self, ayudas, raiz):
        trozos = []
        for a in ayudas or []:
            r = self.recursos.get(a.get("r"))
            if not r:
                continue
            ini, _ = r["_subs"].get(a.get("s"), (1, 1))
            pag = ini + int(a.get("p", 1)) - 1
            texto = f'{esc(a.get("s", ""))} · {esc(a.get("t", ""))} (pág. {int(a.get("p", 1))})'
            if r["_existe"]:
                trozos.append(f'<a class="ver-pdf" href="{raiz}recursos/{quote(r["archivo"])}#page={pag}" target="_blank" '
                              f'rel="noopener noreferrer">{texto}</a>')
            else:
                trozos.append(texto)
        if not trozos:
            return ""
        return '<p class="ayuda"><b>Ayuda en el libro:</b> ' + '<span class="sep">·</span>'.join(trozos) + "</p>"

    def ayuda_paso(self, pid, n):
        d = (self.ayudas.get(pid) or {}).get(str(n))
        return d if isinstance(d, dict) and (d.get("bloques") or d.get("secciones")) else None

    @staticmethod
    def caja_aprenderas(lista, que="proyecto"):
        if not lista:
            return ""
        ico = ["📈", "📐", "🎯", "📏", "✅", "🗣️", "🔍", "🧪", "🧭", "💡"]
        col = ["#38bdf8", "#fbbf24", "#4ade80", "#fb7185", "#a78bfa", "#38bdf8"]
        return (f'<h3 class="ap-t">Al terminar este {que} sabrás:</h3><div class="ap">'
                + "".join(f'<div style="--c:{col[i % len(col)]}"><i>{ico[i % len(ico)]}</i>{esc(x)}</div>'
                          for i, x in enumerate(lista)) + "</div>")

    @staticmethod
    def svg_flujo_hero(f):
        f = f or {"entrada": ["📥", "Datos", "entrada (x)"], "modelo": ["⚙️", "Modelo", "aprende de los datos"],
                  "salida": ["🎯", "Resultado", "salida (y)"]}
        def caja(x, w, y, h, d, col, grande=False):
            t = [esc(v) for v in d]
            relleno = "#0f2747" if grande else "#16213a"
            grosor = ' stroke-width="2"' if grande else ""
            return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{relleno}" stroke="{col}"{grosor}/>'
                    f'<text x="{x + w // 2}" y="{y + 30}" text-anchor="middle" font-size="26">{t[0]}</text>'
                    f'<text x="{x + w // 2}" y="{y + 54}" text-anchor="middle" fill="#e6edf7" font-size="13" font-weight="700">{t[1]}</text>'
                    f'<text x="{x + w // 2}" y="{y + 72}" text-anchor="middle" fill="#9aa8bf" font-size="11">{t[2]}</text>')
        return ('<svg viewBox="0 0 400 190" role="img" aria-label="Entrada, modelo, salida"><defs>'
                '<marker id="fh" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto"><path d="M0 0L8 4L0 8Z" fill="#38bdf8"/></marker></defs>'
                + caja(6, 104, 52, 86, f["entrada"], "#fbbf24")
                + '<line x1="112" y1="95" x2="150" y2="95" stroke="#38bdf8" stroke-width="2" marker-end="url(#fh)"/>'
                + caja(152, 96, 38, 114, f["modelo"], "#38bdf8", True)
                + '<line x1="250" y1="95" x2="288" y2="95" stroke="#38bdf8" stroke-width="2" marker-end="url(#fh)"/>'
                + caja(290, 104, 52, 86, f["salida"], "#4ade80") + '</svg>')

    def resultado_final(self, p, titulo="Si completas este proyecto llegarás a esto", tag="Resultado esperado"):
        f = RAIZ / f"datos--{p['id']}.json"
        if not f.is_file():
            return ""
        try:
            D = json.loads(f.read_text(encoding="utf-8"))
            T, P, E = D["t"], D["p"], D["e"]
            m, b, r2, rmse, mae = D["m"], D["b"], D["r2"], D["rmse"], D["mae"]
        except (ValueError, KeyError, OSError):
            return ""
        x0, x1, y0, y1 = 0.0, 40.0, 415.0, 500.0
        W, H, ml, mb = 720, 380, 56, 44
        X = lambda v: ml + (v - x0) / (x1 - x0) * (W - ml - 12)
        Y = lambda v: 12 + (y1 - v) / (y1 - y0) * (H - mb - 12)
        pts = "".join(f'<circle cx="{X(T[i]):.1f}" cy="{Y(P[i]):.1f}" r="2.3" fill="{"#fbbf24" if E[i] else "#38bdf8"}" fill-opacity=".45"/>'
                      for i in range(0, len(T), 9))
        ejes = "".join(f'<line x1="{X(v):.0f}" y1="12" x2="{X(v):.0f}" y2="{H - mb}" stroke="#22304a"/>'
                       f'<text x="{X(v):.0f}" y="{H - mb + 18}" text-anchor="middle" fill="#9aa8bf" font-size="12">{v}</text>'
                       for v in (0, 10, 20, 30, 40))
        ejes += "".join(f'<line x1="{ml}" y1="{Y(v):.0f}" x2="{W - 12}" y2="{Y(v):.0f}" stroke="#22304a"/>'
                        f'<text x="{ml - 8}" y="{Y(v) + 4:.0f}" text-anchor="end" fill="#9aa8bf" font-size="12">{v}</text>'
                        for v in (420, 440, 460, 480, 500))
        recta = f'<line x1="{X(1.8):.1f}" y1="{Y(m * 1.8 + b):.1f}" x2="{X(37.1):.1f}" y2="{Y(m * 37.1 + b):.1f}" stroke="#4ade80" stroke-width="3.5"/>'
        ecu = f'y = {m:.3f}·x + {b:.2f}'.replace(".", ",").replace("-", "−")
        svg = (f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Nube de puntos y recta de regresión">{ejes}{pts}{recta}'
               f'<rect x="{X(21)}" y="{Y(497)}" width="248" height="30" rx="8" fill="#0f2747" stroke="#4ade80"/>'
               f'<text x="{X(21) + 124}" y="{Y(497) + 20}" text-anchor="middle" fill="#e6edf7" font-size="15" font-weight="700" font-family="monospace">{esc(ecu)}</text>'
               f'<text x="{(W + ml) / 2}" y="{H - 6}" text-anchor="middle" fill="#9aa8bf" font-size="12">Temperatura (°C)</text>'
               f'<text x="14" y="{H / 2 - 20}" fill="#9aa8bf" font-size="12" transform="rotate(-90 14 {H / 2 - 20})">Potencia (MW)</text></svg>')
        num = lambda v, d=2: f"{v:.{d}f}".replace(".", ",")
        kg = ('<div class="kg">'
              f'<div><small>Ecuación</small><strong style="color:#4ade80;font-size:1rem">{esc(ecu)}</strong></div>'
              f'<div><small>R² (prueba)</small><strong style="color:#38bdf8">{num(r2)}</strong></div>'
              f'<div><small>RMSE</small><strong style="color:#fbbf24">{num(rmse)} MW</strong></div>'
              f'<div><small>MAE</small><strong style="color:#fb7185">{num(mae)} MW</strong></div></div>')
        concl = f'<div class="concl"><b>Conclusión:</b> {esc(p.get("conclusion") or p.get("resultados", ""))}</div>'
        return (f'<section class="esperado-g"><span class="etq" style="color:#4ade80;font-size:.72rem;letter-spacing:.1em;text-transform:uppercase;font-weight:700">{esc(tag)}</span>'
                f'<h2 style="--c:#4ade80">{esc(titulo)}</h2>'
                '<p class="sub" style="color:var(--suave);margin:0">Puntos azules: datos de entrenamiento · puntos ámbar: datos de prueba · línea verde: la recta que calcularás.</p>'
                f'{svg}{kg}{concl}</section>')

    def graficos_resultado(self, p):
        if (RAIZ / f"img--{p['id']}--cuaderno.png").is_file():
            self.copiar(RAIZ / f"img--{p['id']}--cuaderno.png", f"img/{p['id']}--cuaderno.png")
            ex = [("1 · Nube de puntos", "Cada punto es una hora de funcionamiento. La nube baja casi en línea recta: una recta tiene sentido."),
                  ("2 · Recta de regresión", "La línea es la recta calculada con los datos de entrenamiento y dibujada sobre los de prueba. Cuanto más pegados, mejor predice."),
                  ("3 · Análisis de residuos", "El error de cada predicción (real − predicho). Repartido al azar alrededor del cero indica que la recta es suficiente.")]
            return ('<h3 class="sec-g">Las gráficas que genera el código del proyecto</h3>'
                    f'<figure class="fig-cuaderno"><img src="../img/{esc(p["id"])}--cuaderno.png" alt="Gráficas generadas por el código: nube de puntos, recta de regresión y residuos" loading="lazy">'
                    '<figcaption>Salida real del código ejecutado en Colab.</figcaption></figure>'
                    '<div class="grafs-res">' + "".join(f'<figure><h4>{esc(t)}</h4><figcaption>{esc(c)}</figcaption></figure>' for t, c in ex) + '</div>')
        reales = []
        for nombre, titulo, texto in (
                ("cuaderno-dispersion.png", "1 · Nube de puntos (plt.scatter)",
                 "Salida real del código en Colab. Cada punto es una hora de funcionamiento: la nube baja casi en línea recta, así que una recta tiene sentido."),
                ("cuaderno-recta.png", "2 · Recta de regresión",
                 "Salida real del código: los datos de prueba (puntos) y la recta calculada con los datos de entrenamiento. Cuanto más pegados a la línea, mejor predice."),
                ("cuaderno-residuos.png", "3 · Análisis de residuos",
                 "Salida real del código: el error de cada predicción (real − predicho). Si se reparten al azar alrededor del cero, la recta es suficiente; una curva o un abanico indicarían que falta algo.")):
            if (RAIZ / f"img--{p['id']}--{nombre}").is_file():
                self.copiar(RAIZ / f"img--{p['id']}--{nombre}", f"img/{p['id']}--{nombre}")
                reales.append(f'<figure><h4>{esc(titulo)}</h4><img src="../img/{esc(p["id"])}--{esc(nombre)}" alt="{esc(titulo)}" loading="lazy">'
                              f'<figcaption>{esc(texto)}</figcaption></figure>')
        if reales:
            return ('<h3 class="sec-g">Las gráficas que genera el código del proyecto</h3><div class="grafs-res">' + "".join(reales) + '</div>')
        f = RAIZ / f"datos--{p['id']}.json"
        if not f.is_file():
            return ""
        try:
            D = json.loads(f.read_text(encoding="utf-8"))
            T, P, E = D["t"], D["p"], D["e"]
            m, b = D["m"], D["b"]
        except (ValueError, KeyError, OSError):
            return ""
        W, H, ml, mb = 520, 320, 52, 40

        def panel(xmin, xmax, ymin, ymax, xt, yt, xl, yl, cuerpo_fn):
            X = lambda v: ml + (v - xmin) / (xmax - xmin) * (W - ml - 10)
            Y = lambda v: 10 + (ymax - v) / (ymax - ymin) * (H - mb - 10)
            g = "".join(f'<line x1="{X(v):.0f}" y1="10" x2="{X(v):.0f}" y2="{H - mb}" stroke="#22304a"/>'
                        f'<text x="{X(v):.0f}" y="{H - mb + 16}" text-anchor="middle" fill="#9aa8bf" font-size="11">{v}</text>' for v in xt)
            g += "".join(f'<line x1="{ml}" y1="{Y(v):.0f}" x2="{W - 10}" y2="{Y(v):.0f}" stroke="#22304a"/>'
                         f'<text x="{ml - 6}" y="{Y(v) + 4:.0f}" text-anchor="end" fill="#9aa8bf" font-size="11">{v}</text>' for v in yt)
            return (f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{esc(xl)} frente a {esc(yl)}">{g}{cuerpo_fn(X, Y)}'
                    f'<text x="{(W + ml) / 2}" y="{H - 6}" text-anchor="middle" fill="#9aa8bf" font-size="11">{esc(xl)}</text>'
                    f'<text x="12" y="{H / 2 - 20}" fill="#9aa8bf" font-size="11" transform="rotate(-90 12 {H / 2 - 20})">{esc(yl)}</text></svg>')

        def nube(X, Y):
            return "".join(f'<circle cx="{X(T[i]):.1f}" cy="{Y(P[i]):.1f}" r="2.2" fill="#38bdf8" fill-opacity=".45"/>'
                           for i in range(0, len(T), 8))

        def recta(X, Y):
            l = (f'<line x1="{X(1.8):.1f}" y1="{Y(m * 1.8 + b):.1f}" x2="{X(37.1):.1f}" y2="{Y(m * 37.1 + b):.1f}" '
                 'stroke="#4ade80" stroke-width="3.5"/>')
            return "".join(f'<circle cx="{X(T[i]):.1f}" cy="{Y(P[i]):.1f}" r="2.2" fill="#fbbf24" fill-opacity=".35"/>'
                           for i in range(0, len(T), 8) if E[i]) + l

        idx = [i for i in range(len(T)) if E[i]]
        res = [(m * T[i] + b, P[i] - (m * T[i] + b)) for i in idx]

        def resid(X, Y):
            c = "".join(f'<circle cx="{X(a):.1f}" cy="{Y(r):.1f}" r="2.2" fill="#a78bfa" fill-opacity=".5"/>' for a, r in res[::2])
            return (c + f'<line x1="{X(425)}" y1="{Y(0):.1f}" x2="{X(495)}" y2="{Y(0):.1f}" stroke="#fb7185" stroke-width="2.5"/>'
                    + "".join(f'<line x1="{X(425)}" y1="{Y(v):.1f}" x2="{X(495)}" y2="{Y(v):.1f}" stroke="#fbbf24" stroke-dasharray="5 4"/>' for v in (-10.5, 10.5)))

        tarjetas = [
            ("1 · Nube de puntos", panel(0, 40, 415, 500, (0, 10, 20, 30, 40), (420, 440, 460, 480, 500), "Temperatura (°C)", "Potencia (MW)", nube),
             "Cada punto es una hora de funcionamiento. La nube baja casi en línea recta: a más calor, menos potencia. Así sabemos, antes de calcular nada, que una recta tiene sentido."),
            ("2 · Recta de regresión", panel(0, 40, 415, 500, (0, 10, 20, 30, 40), (420, 440, 460, 480, 500), "Temperatura (°C)", "Potencia (MW)", recta),
             "La línea verde es la recta que calculas con el código (y = −2,177·x + 497,15) sobre los datos de prueba, que el modelo no vio al aprender. Cuanto más pegados a la línea, mejor predice."),
            ("3 · Análisis de residuos", panel(425, 495, -32, 32, (430, 450, 470, 490), (-30, -20, -10, 0, 10, 20, 30), "Potencia predicha (MW)", "Error (MW)", resid),
             "Cada punto es el error de una predicción. Si se reparten al azar alrededor de la línea roja (error 0) y casi todos caen entre las amarillas (±10,5 MW), el modelo no tiene sesgo y la recta es suficiente."),
        ]
        return ('<div class="grafs-res">' + "".join(
            f'<figure><h4>{t}</h4>{svg}<figcaption>{esc(c)}</figcaption></figure>' for t, svg, c in tarjetas) + '</div>')

    def hero_proyecto(self, p, npasos):
        est = p.get("estado", "idea")
        nivel = (p.get("nivel") or "").strip().lower()
        chips = [("c1", f'Nivel {self.NIVEL_TXT.get(nivel, nivel)}', "#4ade80")]
        if p.get("area"):
            chips.append(("c2", str(p["area"]).capitalize(), "#38bdf8"))
        if p.get("tecnica"):
            chips.append(("c3", p["tecnica"], "#fbbf24"))
        if p.get("registros"):
            chips.append(("c4", p["registros"], "#a78bfa"))
        ch = "".join(f'<span class="chip2" style="color:{c};border-color:{c}77">{esc(t)}</span>' for _, t, c in chips)
        meta = []
        if p.get("tiempo"):
            meta.append(f'⏱ ≈ {esc(p["tiempo"])}')
        if npasos:
            meta.append(f'{npasos} pasos')
        if p.get("herramientas"):
            meta.append(esc(", ".join(p["herramientas"])))
        return (f'<section class="hero"><div><span class="etq">{esc(self.BLOQUES_TXT.get(p.get("bloque"), "Proyecto"))} · '
                f'{esc(self.NIVEL_TXT.get(nivel, nivel))} · {esc(self.ESTADOS.get(est, est))}</span>'
                f'<h1>{esc(p.get("titulo", ""))}</h1><p class="sub">{esc(p.get("descripcion", ""))}</p>'
                f'<div class="chips2">{ch}</div><p class="sub">{" · ".join(meta)}</p></div>'
                f'<div class="flujo-h">{self.svg_flujo_hero(p.get("flujo"))}</div></section>')

    BLOQUES_TXT = {"regresion": "Regresión", "clasificacion": "Clasificación", "redes": "Redes neuronales", "experto": "Experto"}

    @staticmethod
    def red_progreso(pid, titulos):
        n = len(titulos)
        if n < 2:
            return ""
        ys = [75, 40, 105, 55, 95, 40, 110, 60, 90, 75]
        X = lambda i: 60 + i * (840 / (n - 1))
        Y = lambda i: ys[i % len(ys)]
        lin = "".join(f'<line class="rl" data-i="{i}" x1="{X(i):.0f}" y1="{Y(i)}" x2="{X(i + 1):.0f}" y2="{Y(i + 1)}" stroke="#22304a" stroke-width="1.6"/>'
                      for i in range(n - 1))
        nod = "".join(f'<a href="#paso-{i + 1}"><g class="rn" data-i="{i + 1}"><title>{esc(t)}</title>'
                      f'<circle cx="{X(i):.0f}" cy="{Y(i)}" r="16" fill="#16213a" stroke="#22304a" stroke-width="2"/>'
                      f'<text x="{X(i):.0f}" y="{Y(i) + 5}" text-anchor="middle" fill="#e6edf7" font-size="13" font-weight="700">{i + 1}</text></g></a>'
                      for i, t in enumerate(titulos))
        return (f'<div class="red" data-red="{esc(pid)}"><h3 style="margin:0 0 6px;font-size:1.05rem">Tu recorrido: una red neuronal que se ilumina</h3>'
                f'<svg viewBox="0 0 960 150" role="img" aria-label="Progreso por pasos">{lin}{nod}</svg>'
                '<p>Cada nodo es un paso. Al marcarlo como completado se enciende en verde y se conecta con el siguiente. Pulsa un nodo para ir a él.</p></div>')

    def bloques_html(self, bloques, pid=""):
        out = []
        for b in bloques:
            t = b.get("t")
            if t == "sec":
                out.append(f'<h3 class="sec">{esc(b.get("x", ""))}<span class="pag">{esc(b.get("pag", ""))}</span></h3>')
            elif t == "h":
                out.append(f'<h4>{esc(b.get("x", ""))}</h4>')
            elif t == "p":
                out.append(f'<p>{esc(b.get("x", ""))}</p>')
            elif t == "ul":
                out.append("<ul>" + "".join(f"<li>{esc(x)}</li>" for x in b.get("x", [])) + "</ul>")
            elif t == "etq":
                k = b.get("k", "sencilla")
                k = k if k in ("sencilla", "atencion", "nota", "regla") else "sencilla"
                out.append(f'<div class="callout {k}"><b>{esc(b.get("titulo", ""))}</b>{esc(b.get("x", ""))}</div>')
            elif t == "tabla":
                cab = "".join(f"<th>{esc(c)}</th>" for c in b.get("cab", []))
                filas = "".join("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in f) + "</tr>" for f in b.get("filas", []))
                pie = b.get("pie")
                tf = ("<tfoot><tr>" + "".join(f"<td>{esc(c)}</td>" for c in pie) + "</tr></tfoot>") if pie else ""
                out.append(f'<div class="tabla-scroll"><table class="tabla-libro"><thead><tr>{cab}</tr></thead>'
                           f'<tbody>{filas}</tbody>{tf}</table></div>')
                if b.get("nota"):
                    out.append(f'<p class="tabla-nota">{esc(b["nota"])}</p>')
            elif t == "code":
                x = b.get("x", "")
                abierto = " open" if x.count("\n") < 24 else ""
                out.append(f'<details class="codigo"{abierto}><summary>{esc(b.get("titulo", "Código"))}</summary>'
                           f'<button class="copiar" type="button">Copiar</button><pre class="cod"><code>{esc(x)}</code></pre></details>')
            elif t == "salida":
                out.append(f'<p class="etiqueta-salida">Salida real del programa</p><pre class="salida">{esc(b.get("x", ""))}</pre>')
            elif t == "lab":
                out.append(self.lab_html(pid, b))
            elif t == "graf":
                out.append(self.graf_html(pid, b))
            elif t == "leer":
                filas = [("👀 Qué ves", b.get("ver"), "#38bdf8"), ("🧭 Cómo se lee", b.get("leer"), "#a78bfa"),
                         ("💡 Qué nos dice aquí", b.get("dice"), "#4ade80")]
                cuerpo = "".join(f'<div style="--c:{c}"><b>{e}</b><span>{esc(x)}</span></div>' for e, x, c in filas if x)
                if b.get("ojo"):
                    cuerpo += f'<div class="ojo"><span>⚠️ <b style="display:inline;color:#fbbf24">Ojo:</b> {esc(b["ojo"])}</span></div>'
                out.append(f'<div class="leer">{cuerpo}</div>')
            elif t in ("nubes3", "patrones"):
                out.append(self.svg_estaticos(t))
            elif t == "flujo":
                out.append(self.svg_flujo())
            elif t == "gauge":
                try:
                    v = max(0.0, min(1.0, float(b.get("valor", 0))))
                except (TypeError, ValueError):
                    v = 0.0
                out.append('<div class="gauge-b"><svg viewBox="0 0 120 78"><path d="M10 68 A50 50 0 0 1 110 68" fill="none" stroke="#22304a" '
                           'stroke-width="12" stroke-linecap="round"/><path d="M10 68 A50 50 0 0 1 110 68" fill="none" stroke="#38bdf8" '
                           f'stroke-width="12" stroke-linecap="round" stroke-dasharray="157" stroke-dashoffset="{157 * (1 - v):.1f}"/>'
                           f'<text x="60" y="64" text-anchor="middle" fill="#e6edf7" font-size="22" font-weight="800" font-family="monospace">'
                           f'{str(round(v, 2)).replace(".", ",")}</text></svg><small>{esc(b.get("etq", ""))}</small></div>')
            elif t == "kpis":
                out.append('<div class="kpis-g">' + "".join(
                    f'<div class="kpi-g" style="--c:{esc(k.get("c", "#38bdf8"))}"><strong>{esc(k.get("v", ""))}</strong>'
                    f'<small>{esc(k.get("x", ""))}</small></div>' for k in b.get("items", [])) + "</div>")
            elif t == "glosa":
                out.append('<table class="glosa"><tbody>' + "".join(
                    f'<tr><td>{esc(a)}</td><td>{esc(c)}</td></tr>' for a, c in b.get("filas", [])) + "</tbody></table>")
            elif t == "img":
                nombre = b.get("archivo", "")
                origen = RAIZ / f"img--{pid}--{nombre}"
                if not origen.is_file() and nombre.startswith("cuaderno-") and (RAIZ / f"img--{pid}--cuaderno.png").is_file():
                    nombre = "cuaderno.png"
                    origen = RAIZ / f"img--{pid}--{nombre}"
                if origen.is_file():
                    self.copiar(origen, f"img/{pid}--{nombre}")
                    out.append(f'<figure class="fig" style="max-width:720px"><img class="pasos-img" loading="lazy" '
                               f'src="../img/{esc(pid)}--{esc(nombre)}" alt="{esc(b.get("x", ""))}">'
                               f'<figcaption>{esc(b.get("x", ""))}</figcaption></figure>')
                else:
                    out.append(f'<div class="labr-falta">Falta la imagen <b>img--{esc(pid)}--{esc(nombre)}</b> en la raíz del repositorio.</div>')
            elif t == "cards":
                cols = ("#38bdf8", "#fbbf24", "#4ade80", "#fb7185")
                out.append('<div class="cards4">' + "".join(
                    f'<div style="--c:{cols[i % 4]}"><b>{esc(c.get("t", ""))}</b>{esc(c.get("x", ""))}</div>'
                    for i, c in enumerate(b.get("items", []))) + "</div>")
            elif t == "lineas":
                filas = "".join(f"<tr><td>{esc(a)}</td><td>{esc(q)}</td></tr>" for a, q in b.get("filas", []))
                out.append('<div class="tabla-scroll"><table class="tabla-libro lineas"><thead><tr><th>En el código</th>'
                           f'<th>Qué hace</th></tr></thead><tbody>{filas}</tbody></table></div>')
            elif t == "colab":
                u = enlace_seguro(b.get("url"))
                pasos_c = "".join(f"<li>{esc(x)}</li>" for x in b.get("pasos", []))
                boton = (f'<a class="boton verde" href="{esc(u)}" target="_blank" rel="noopener noreferrer">▶ Abrir en Google Colab</a>'
                         if u.startswith("https://") else "")
                out.append(f'<div class="colab">{boton}<ol>{pasos_c}</ol></div>')
            elif t == "esperado":
                out.append('<div class="esperado">' + "".join(
                    f'<div class="esp"><small>{esc(a)}</small><strong>✓ {esc(v)}</strong></div>' for a, v in b.get("items", [])) + "</div>")
            elif t == "kpis":
                out.append('<div class="res4">' + "".join(
                    f'<div style="--c:{esc(c.get("c", "#38bdf8"))}"><strong>{esc(c.get("v", ""))}</strong><small>{esc(c.get("x", ""))}</small></div>'
                    for c in b.get("items", [])) + "</div>")
            elif t == "fig":
                out.append(f'<figure class="fig">{b.get("svg", "")}<figcaption>{esc(b.get("x", ""))}</figcaption></figure>')
        return "".join(out)

    @staticmethod
    def evidencias_de(pid, n):
        patron = re.compile(rf"^{re.escape(pid)}--p{n}--(.+)\.([A-Za-z0-9]+)$")
        hallados = []
        for carpeta in (RAIZ, RAIZ / "evidencias"):
            if not carpeta.is_dir():
                continue
            for f in sorted(carpeta.iterdir()):
                m = patron.match(f.name)
                if f.is_file() and m and m.group(2).lower() in ("png", "jpg", "jpeg", "gif", "webp", "svg",
                                                                 "py", "txt", "ipynb", "pdf", "csv"):
                    hallados.append((f, m.group(1).replace("-", " ").strip(), m.group(2).lower()))
        return hallados

    def evidencias_html(self, pid, n, d):
        items = self.evidencias_de(pid, n)
        cab = f'<p>{esc(d.get("evidencias", ""))}</p>' if d.get("evidencias") else ""
        if not items:
            ejemplo = f"{pid}--p{n}--grafico-dispersion.png"
            return (cab + '<div class="evid-vacia">Todavía no hay nada subido en este paso.<br>'
                    'Para añadir una imagen, un código (.py, .txt) o un cuaderno (.ipynb), sube el archivo a la raíz '
                    f'del repositorio con este nombre: <code class="nombre">{esc(ejemplo)}</code><br>'
                    f'Lo que va entre <code class="nombre">--p{n}--</code> y la extensión es el título que se mostrará.</div>')
        cuerpo = []
        for f, titulo, ext in items:
            destino = f"evidencias/{f.name}"
            self.copiar(f, destino)
            if ext in ("png", "jpg", "jpeg", "gif", "webp", "svg"):
                cuerpo.append(f'<figure><a href="../{esc(destino)}" target="_blank" rel="noopener noreferrer">'
                              f'<img src="../{esc(destino)}" alt="{esc(titulo)}" loading="lazy"></a>'
                              f'<figcaption>{esc(titulo)}</figcaption></figure>')
            elif ext in ("py", "txt") and f.stat().st_size < 80000:
                txt = f.read_text(encoding="utf-8", errors="replace")
                cuerpo.append(f'<figure style="grid-column:1/-1"><figcaption>{esc(titulo)} · <a href="../{esc(destino)}" '
                              f'download>descargar</a></figcaption><details class="codigo" open><summary>Código</summary>'
                              f'<button class="copiar" type="button">Copiar</button><pre class="cod"><code>{esc(txt)}</code></pre></details></figure>')
            else:
                cuerpo.append(f'<figure><a href="../{esc(destino)}" target="_blank" rel="noopener noreferrer">{esc(titulo)}'
                              f' ({esc(ext)}) ↗</a></figure>')
        return cab + '<div class="evid">' + "".join(cuerpo) + "</div>"

    def copiar(self, origen, destino_rel):
        d = self.salida / destino_rel
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(origen, d)

    def lab_html(self, pid, b):
        modo = b.get("modo") if b.get("modo") in ("nube", "residuos") else "recta"
        titulo = esc(b.get("titulo") or {"nube": "La nube de puntos real", "residuos": "Los errores de la recta (residuos)"}.get(modo, "Laboratorio: mueve la recta"))
        sub = esc(b.get("x") or "")
        sel = ('<label style="display:block">Datos que se miden<select><option value="train">Entrenamiento (80 %)</option>'
               '<option value="test">Prueba (20 %)</option><option value="todos">Todos</option></select></label>')
        if modo == "residuos":
            ctl = ('<label style="display:block">Datos que se ven<select><option value="test">Prueba (20 %)</option>'
                   '<option value="train">Entrenamiento (80 %)</option><option value="todos">Todos</option></select></label>'
                   '<div class="labr-kpis"><div class="labr-kpi"><small>Puntos</small><strong class="k-n">–</strong></div>'
                   '<div class="labr-kpi"><small>Error medio</small><strong class="k-rm" style="font-size:.95rem">–</strong></div>'
                   '<div class="labr-kpi"><small>Desviación σ</small><strong class="k-rs" style="font-size:.95rem">–</strong></div>'
                   '<div class="labr-kpi"><small>Error máximo</small><strong class="k-rx" style="font-size:.95rem">–</strong></div></div>')
        elif modo == "nube":
            ctl = ('<label style="display:block">Datos que se ven<select><option value="todos">Todos</option>'
                   '<option value="train">Entrenamiento (80 %)</option><option value="test">Prueba (20 %)</option></select></label>'
                   + '<div class="chk"><input class="rec" type="checkbox"' + (' checked' if b.get("rec") else '') + ' id="rec-' + esc(pid) + '"><label for="rec-' + esc(pid) + '" style="display:inline;margin:0">Dibujar la recta que calculará el programa</label></div>'
                   '<div class="labr-kpis"><div class="labr-kpi"><small>Registros</small><strong class="k-n">–</strong></div>'
                   '<div class="labr-kpi"><small>Correlación</small><strong class="k-cor">–</strong></div>'
                   '<div class="labr-kpi"><small>Temperatura</small><strong class="k-rt" style="font-size:.85rem">–</strong></div>'
                   '<div class="labr-kpi"><small>Potencia</small><strong class="k-rp" style="font-size:.85rem">–</strong></div></div>')
        else:
            ctl = ('<label>Pendiente m (MW por °C) <b class="mv">–</b></label><input class="m" type="range" min="-5" max="1" step="0.01" value="0">'
                   '<label>Intercepto b (MW) <b class="bv">–</b></label><input class="b" type="range" min="300" max="700" step="0.1" value="450">'
                   '<div class="chk"><input class="piv" type="checkbox" id="piv-' + esc(pid) + '"><label for="piv-' + esc(pid) + '" style="display:inline;margin:0">'
                   'Que la recta gire alrededor del centro de los datos (siempre pasa por la media)</label></div>'
                   + sel +
                   '<div class="labr-eq k-eq">–</div>'
                   '<div class="labr-kpis"><div class="labr-kpi"><small>SSE</small><strong class="k-sse">–</strong></div>'
                   '<div class="labr-kpi"><small>R²</small><strong class="k-r2">–</strong></div>'
                   '<div class="labr-kpi"><small>RMSE</small><strong class="k-rmse">–</strong></div>'
                   '<div class="labr-kpi"><small>MAE</small><strong class="k-mae">–</strong></div></div>'
                   '<div class="labr-barra"><i></i></div><div class="k-ratio" style="font-size:.8rem;color:var(--suave);margin-top:4px"></div>'
                   '<button class="boton verde b-sol" type="button">✨ Ir a la solución del programa</button>'
                   '<button class="boton b-cero" type="button">↺ Empezar con una recta plana</button>')
        return (f'<div class="labr" data-src="../datos/{esc(pid)}.json" data-modo="{modo}" data-id="{esc(pid)}">'
                f'<h3>{"📊" if modo == "nube" else "🧪"} {titulo}</h3>'
                + (f'<p class="labr-sub">{sub}</p>' if sub else "")
                + f'<div class="labr-cuerpo"><canvas role="img" aria-label="Gráfico con los datos reales de temperatura y potencia"></canvas>'
                  f'<div class="labr-ctl">{ctl}<div class="labr-msg"></div></div></div></div>')

    def graf_html(self, pid, b):
        modo = b.get("modo", "hist")
        titulos = {"hist": "Histograma", "reparto": "El reparto 80 / 20", "realpred": "Real frente a predicho",
                   "banda": "La predicción con su rango del 95 %", "anatomia": "Las dos piezas de la recta"}
        iconos = {"hist": "📊", "reparto": "🧩", "realpred": "🎯", "banda": "🔮", "anatomia": "📐"}
        titulo = esc(b.get("titulo") or titulos.get(modo, "Gráfico"))
        sub = esc(b.get("x") or "")
        kp = lambda lista: '<div class="labr-kpis">' + "".join(
            f'<div class="labr-kpi"><small>{esc(n)}</small><strong class="{c}" style="font-size:.95rem">–</strong></div>' for n, c in lista) + "</div>"
        sld = lambda etq, mn, mx, st, v: (f'<label>{etq} <b class="v1">{v}</b></label>'
                                          f'<input class="s1" type="range" min="{mn}" max="{mx}" step="{st}" value="{v}">')
        sel = ('<label style="display:block">Datos que se ven<select><option value="test">Prueba (20 %)</option>'
               '<option value="train">Entrenamiento (80 %)</option><option value="todos">Todos</option></select></label>')
        if modo == "hist":
            ctl = sld("Número de barras", 8, 50, 1, 24) + kp([("Registros", "k-n"), ("Media", "k-me"), ("Mediana", "k-md"),
                                                               ("Desviación σ", "k-sd"), ("Mínimo", "k-mn"), ("Máximo", "k-mx")])
        elif modo == "reparto":
            ctl = kp([("Entrenamiento", "k-tr"), ("Prueba", "k-te")])
        elif modo == "realpred":
            ctl = sel + sld("Tolerancia ± (MW)", 1, 15, 1, 5) + kp([("R²", "k-r2"), ("RMSE", "k-rmse"), ("MAE", "k-mae"), ("Dentro de ±tolerancia", "k-in")])
        elif modo == "banda":
            ctl = sld("Temperatura (°C)", 0, 45, 0.5, 25) + kp([("Predicción", "k-h"), ("Estado", "k-es"),
                                                                 ("Límite inferior", "k-lo"), ("Límite superior", "k-hi")])
        else:
            modo = "anatomia"
            ctl = sld("Subida de temperatura (°C)", 1, 10, 1, 5) + kp([("Pendiente m", "k-m"), ("Intercepto b", "k-b"), ("Cambio de potencia", "k-d")])
        extra = ""
        if b.get("var"):
            extra += f' data-var="{esc(b["var"])}"'
        if b.get("temp") is not None and modo == "banda":
            extra += f' data-t="{esc(str(b["temp"]))}"'
        return (f'<div class="labr grx" data-src="../datos/{esc(pid)}.json" data-modo="{modo}" data-id="{esc(pid)}"{extra}>'
                f'<h3>{iconos.get(modo, "📈")} {titulo}</h3>'
                + (f'<p class="labr-sub">{sub}</p>' if sub else "")
                + '<div class="labr-cuerpo"><canvas role="img" aria-label="Gráfico con los datos reales de la central"></canvas>'
                  f'<div class="labr-ctl">{ctl}<div class="labr-msg"></div></div></div></div>')

    @staticmethod
    def svg_estaticos(tipo):
        import random
        rnd = random.Random(11)
        W, H = 200, 140
        def marco(extra):
            return (f'<svg viewBox="0 0 {W} {H}" class="fig-svg" aria-hidden="true">'
                    f'<line x1="14" y1="{H-14}" x2="{W-8}" y2="{H-14}" stroke="#64748b"/><line x1="14" y1="8" x2="14" y2="{H-14}" stroke="#64748b"/>'
                    + extra + '</svg>')
        def pts(fn, n=46, col="#fbbf24"):
            o = []
            for _ in range(n):
                x = rnd.uniform(0.04, 0.96); y = fn(x)
                o.append(f'<circle cx="{14 + x*(W-26):.1f}" cy="{(H-14) - max(0.03, min(0.97, y))*(H-26):.1f}" r="2.6" fill="{col}" opacity=".85"/>')
            return "".join(o)
        if tipo == "nubes3":
            a = marco(pts(lambda x: 0.12 + 0.76*x + rnd.gauss(0, 0.07)) + f'<line x1="22" y1="{H-30}" x2="{W-14}" y2="22" stroke="#38bdf8" stroke-width="2"/>')
            b = marco(pts(lambda x: 0.5 + rnd.gauss(0, 0.2)))
            c = marco(pts(lambda x: 0.88 - 0.76*x + rnd.gauss(0, 0.07), col="#38bdf8") + f'<line x1="22" y1="22" x2="{W-14}" y2="{H-30}" stroke="#4ade80" stroke-width="2"/>')
            fig = [("", a, "<b>Relación positiva</b>: más X, más Y. Ejemplo: horas de estudio → nota."),
                   ("", b, "<b>Sin relación</b>: la nube es redonda y la recta no sirve de nada."),
                   ("este", c, "<b>Relación negativa</b>: más X, menos Y. <b>Es la nuestra</b>: más temperatura, menos potencia.")]
        else:
            a = marco(pts(lambda x: 0.5 + rnd.gauss(0, 0.09), col="#38bdf8") + f'<line x1="14" y1="{(H-14)-0.5*(H-26):.0f}" x2="{W-8}" y2="{(H-14)-0.5*(H-26):.0f}" stroke="#fb7185" stroke-dasharray="4 3" stroke-width="1.6"/>')
            b = marco(pts(lambda x: 0.28 + 1.9*(x-0.5)**2 + rnd.gauss(0, 0.04), col="#fbbf24") + f'<line x1="14" y1="{(H-14)-0.5*(H-26):.0f}" x2="{W-8}" y2="{(H-14)-0.5*(H-26):.0f}" stroke="#fb7185" stroke-dasharray="4 3" stroke-width="1.6"/>')
            c = marco(pts(lambda x: 0.5 + rnd.gauss(0, 0.02 + 0.16*x), col="#fbbf24") + f'<line x1="14" y1="{(H-14)-0.5*(H-26):.0f}" x2="{W-8}" y2="{(H-14)-0.5*(H-26):.0f}" stroke="#fb7185" stroke-dasharray="4 3" stroke-width="1.6"/>')
            fig = [("este", a, "<b>👍 Aleatorio</b>: los errores se reparten sin forma alrededor del cero. La recta es suficiente."),
                   ("", b, "<b>⚠️ Curva</b>: la recta se deja una relación que no es recta. Hace falta otro modelo."),
                   ("", c, "<b>⚠️ Abanico</b>: el error crece hacia un lado. El modelo falla más en un extremo.")]
        return '<div class="estaticos">' + "".join(
            f'<figure class="{c}">{svg}<figcaption>{cap}</figcaption></figure>' for c, svg, cap in fig) + "</div>"

    @staticmethod
    def svg_flujo():
        def caja(x, w, tit, l1, l2, col):
            return (f'<rect x="{x}" y="14" width="{w}" height="92" rx="14" fill="#16213a" stroke="{col}" stroke-width="1.6"/>'
                    f'<text x="{x + w/2}" y="40" text-anchor="middle" fill="#e6edf7" font-size="13" font-weight="700">{tit}</text>'
                    f'<text x="{x + w/2}" y="62" text-anchor="middle" fill="#9aa8bf" font-size="11">{l1}</text>'
                    f'<text x="{x + w/2}" y="80" text-anchor="middle" fill="{col}" font-size="12" font-weight="700">{l2}</text>')
        flecha = lambda x: (f'<line x1="{x}" y1="60" x2="{x + 38}" y2="60" stroke="#38bdf8" stroke-width="2" marker-end="url(#fl)"/>')
        return ('<svg viewBox="0 0 760 120" class="flujo-svg fig-svg" role="img" aria-label="De la tabla de UCI a nuestra tabla df">'
                '<defs><marker id="fl" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto"><path d="M0 0L8 4L0 8Z" fill="#38bdf8"/></marker></defs>'
                + caja(6, 220, "Repositorio UCI nº 294", "9.568 filas × 5 columnas", "AT · V · AP · RH · PE", "#a78bfa")
                + flecha(232) + caja(272, 220, "Nos quedamos con 2", "AT → Temperatura (x)", "PE → Potencia (y)", "#fbbf24")
                + flecha(498) + caja(538, 216, "Nuestra tabla «df»", "9.568 filas × 2 columnas", "lista para trabajar", "#4ade80")
                + '</svg>')

    def copiar_datos(self, pid):
        origen = RAIZ / f"datos--{pid}.json"
        if origen.is_file():
            self.copiar(origen, f"datos/{pid}.json")
            self.escribir(f"datos/{pid}.js", "window.MMD=window.MMD||{};window.MMD["+json.dumps(pid)+"]="+origen.read_text(encoding="utf-8")+";")
        else:
            print(f"  [AVISO] Falta datos--{pid}.json (súbelo a la raíz del repositorio) para los gráficos con datos reales.")

    def paginas_pasos(self):
        repo = (self.cfg.get("sitio", {}) or {}).get("repo", "pj1967/vida_util")
        for p in self.proyectos:
            pasos = p.get("pasos") or []
            if any(self.ayuda_paso(p["id"], n) for n in range(1, len(pasos) + 1)):
                self.copiar_datos(p["id"])
            for n in range(1, len(pasos) + 1):
                d = self.ayuda_paso(p["id"], n)
                if not d:
                    continue
                pid = p["id"]
                clave = f"{pid}:{n}"
                prev = (f'<a class="enlace-paso" href="{pid}-paso-{n - 1}.html">← Paso anterior</a>'
                        if n > 1 and self.ayuda_paso(pid, n - 1) else "")
                sig = (f'<a class="enlace-paso" href="{pid}-paso-{n + 1}.html">Siguiente paso →</a>'
                       if self.ayuda_paso(pid, n + 1) else
                       (f'<a class="enlace-paso" href="{pid}.html#paso-{n + 1}">Volver al proyecto: paso {n + 1} →</a>'
                        if n < len(pasos) else f'<a class="enlace-paso" href="{pid}.html">Volver al proyecto →</a>'))
                test = d.get("test") or {}
                if test.get("preguntas"):
                    datos = json.dumps(test, ensure_ascii=False).replace("</", "<\\/")
                    caja_test = (f'<script type="application/json" id="test-datos">{datos}</script>'
                                 '<p class="sub-test">Test de '
                                 f'{int(test.get("cuantas", 8))} preguntas al azar; las respuestas cambian de orden cada vez. '
                                 f'Se aprueba con un {int(test.get("aprobado", 70))} %.</p>'
                                 '<div id="test-cuerpo"></div>')
                else:
                    caja_test = ""
                nuevo = bool(d.get("codigo"))
                partes = [f'<p class="migas"><a href="{esc(pid)}.html#paso-{n}">← {esc(p.get("titulo", ""))}</a></p>',
                          f'<div class="paso-pag"><h2 style="--c:#4ade80">Paso {n} de {len(pasos)} · '
                          f'{esc(d.get("titulo") or pasos[n - 1].get("titulo", ""))}</h2>',
                          f'<p class="fuente">{esc(d.get("fuente", ""))}</p>']
                if d.get("intro"):
                    partes.append(f'<p>{esc(d["intro"])}</p>')
                cpp = d.get("cpp")
                if cpp:
                    partes.append('<div class="cpp">'
                                  f'<div style="--c:#38bdf8"><b>🎯 Qué hacemos</b>{esc(cpp.get("que", ""))}</div>'
                                  f'<div style="--c:#a78bfa"><b>🔧 Cómo</b>{esc(cpp.get("como", ""))}</div>'
                                  f'<div style="--c:#fbbf24"><b>💡 Por qué</b>{esc(cpp.get("porque", ""))}</div>'
                                  f'<div style="--c:#4ade80"><b>🚀 Para qué</b>{esc(cpp.get("para", ""))}</div></div>')
                if d.get("secciones"):
                    for sc in d["secciones"]:
                        partes.append(f'<section><h2 style="--c:{esc(sc.get("c", "#38bdf8"))}">{esc(sc.get("icono", ""))} '
                                      f'{esc(sc.get("titulo", ""))}<small>{esc(sc.get("sub", ""))}</small></h2>'
                                      + self.bloques_html(sc.get("bloques", []), pid) + '</section>')
                    partes.append('<section class="caja-paso" id="test" data-clave="' + esc(clave) + '">'
                                  '<h2 style="--c:#fb7185">🧠 Interpreta el resultado</h2>' + caja_test + '</section>')
                elif nuevo:
                    if d.get("explicacion"):
                        partes.append('<section><h2 style="--c:#38bdf8">📖 Explicación<small>antes de ejecutar nada</small></h2>'
                                      + self.bloques_html(d["explicacion"], pid) + '</section>')
                    gl = d.get("glosa")
                    codigo = d["codigo"]
                    partes.append('<section><h2 style="--c:#a78bfa">💻 Código<small>el mismo que hay en el cuaderno</small></h2>'
                                  f'<details class="codigo" open><summary>Python</summary><button class="copiar" type="button">Copiar</button>'
                                  f'<pre class="cod"><code>{esc(codigo)}</code></pre></details>'
                                  + (('<h4>Qué hace cada parte</h4>' + self.bloques_html([{"t": "glosa", "filas": gl}], pid)) if gl else "")
                                  + '</section>')
                    colab = f"https://colab.research.google.com/github/{repo}/blob/main/{pid}.ipynb"
                    partes.append('<section><h2 style="--c:#fbbf24">▶ Ejecutar<small>en Google Colab, gratis</small></h2>'
                                  f'<p>Abre el cuaderno y ejecuta la celda <b>{esc(d.get("celda", "Paso " + str(n)))}</b> con el botón ▶ '
                                  '(necesitas una cuenta de Google). Las celdas anteriores tienen que estar ejecutadas.</p>'
                                  f'<a class="btn-colab" href="{esc(colab)}" target="_blank" rel="noopener noreferrer">▶ Abrir el cuaderno en Colab</a></section>')
                    if d.get("resultado"):
                        partes.append('<section><h2 style="--c:#4ade80">📊 Resultado<small>lo que debe salir al ejecutar</small></h2>'
                                      + self.bloques_html(d["resultado"], pid) + '</section>')
                    partes.append('<section class="caja-paso" id="test" data-clave="' + esc(clave) + '">'
                                  '<h2 style="--c:#fb7185">🧠 Interpreta el resultado</h2>'
                                  + (self.bloques_html(d["interpreta"], pid) if d.get("interpreta") else "")
                                  + caja_test + '</section>')
                else:
                    partes.append('<section><h2 style="--c:#38bdf8">1 · Lee la ayuda<small>extraída del libro, en su mismo orden</small></h2>'
                                  + self.bloques_html(d.get("bloques", []), pid) + '</section>')
                    if caja_test:
                        partes.append('<section class="caja-paso" id="test" data-clave="' + esc(clave) + '">'
                                      '<h2 style="--c:#fbbf24">2 · Comprueba lo aprendido</h2>' + caja_test + '</section>')
                partes.append('<section class="caja-paso"><h2 style="--c:#4ade80">✓ Cierra el paso</h2>'
                              '<p>Cuando hayas leído, ejecutado y aprobado el test, márcalo. '
                              'La marca se guarda en este navegador y se refleja en la página del proyecto.</p>'
                              f'<button id="marcar-paso" class="boton verde" type="button" data-clave="{esc(clave)}">'
                              'Marcar este paso como completado</button></section>')
                partes.append(f'<div class="nav-pasos"><span>{prev}</span><span>{sig}</span></div></div>')
                self.escribir(f"proyectos/{pid}-paso-{n}.html", self.pagina(
                    f"Paso {n}: {d.get('titulo') or pasos[n - 1].get('titulo', '')}", "".join(partes), "../", "proyectos"))

    def pagina_biblioteca(self):
        if not self.recursos:
            return
        bloques = []
        for r in self.recursos.values():
            filas = []
            for sm in r.get("submodulos", []):
                ini, n = r["_subs"][sm["n"]]
                t = esc(sm["titulo"])
                if r["_existe"]:
                    t = f'<a class="ver-pdf" href="recursos/{quote(r["archivo"])}#page={ini}" target="_blank" rel="noopener noreferrer">{t}</a>'
                filas.append(f'<tr><td>{esc(sm["n"])}</td><td>{t}</td><td>{esc(sm.get("nivel", ""))}</td>'
                             f'<td>{n} págs.</td></tr>')
            u = "recursos/" + quote(r["archivo"]) if r["_existe"] else ""
            dl = (f'<p class="botones-pdf"><a class="btn-descarga" href="{u}" download="{esc(r["archivo"])}">⬇ Descargar PDF · {esc(r["titulo"])}</a> '
                  f'<a class="ver-pdf" href="{u}" target="_blank" rel="noopener noreferrer">Abrir en el navegador ↗</a></p>') if r["_existe"] else \
                 '<p class="vacio">El PDF aún no está publicado.</p>'
            bloques.append(f'<h3>{esc(r["titulo"])}</h3><p class="desc">{esc(r.get("autor", ""))}. '
                           f'{esc(r.get("descripcion", ""))}</p>{dl}'
                           '<table class="tabla-libro"><tr><th>Nº</th><th>Submódulo</th><th>Nivel</th><th>Extensión</th></tr>'
                           + "".join(filas) + "</table>")
        cuerpo = ('<h2 style="--c:#38bdf8">Biblioteca<small>apuntes de apoyo a los proyectos</small></h2>'
                  + "".join(bloques))
        self.escribir("biblioteca.html", self.pagina(
            "Biblioteca", cuerpo, "", "biblioteca", descripcion="Apuntes de apoyo a los proyectos."))

    def copiar_recursos(self):
        for r in self.recursos.values():
            f = self.localizar_recurso(r.get("archivo", ""))
            if f:
                (self.salida / "recursos").mkdir(exist_ok=True)
                shutil.copy(f, self.salida / "recursos" / f.name)
            else:
                print(f"  [AVISO] Falta el PDF {r.get('archivo')} (súbelo a la raíz del repositorio).")

    def generar(self):
        if self.salida.exists():
            shutil.rmtree(self.salida)
        self.salida.mkdir(parents=True)
        self.escribir("estilo.css", CSS)
        self.escribir("interactivo.js", JS)
        self.escribir(".nojekyll", "")
        self.portada()
        self.pagina_noticias()
        self.paginas_tema()
        self.pagina_resumenes()
        self.pagina_proyectos()
        self.paginas_pasos()
        self.pagina_retos()
        self.sobre()
        self.copiar_recursos()
        self.pagina_biblioteca()
        self.archivo()


# ----------------------------------------------------------------- principal
def main():
    p = argparse.ArgumentParser(description="Genera la web de noticias.")
    p.add_argument("--config", default=str(RAIZ / "feeds.json"))
    p.add_argument("--datos", default=str(RAIZ / "data" / "articulos.json"))
    p.add_argument("--resumenes", default=str(RAIZ / "data" / "resumenes"))
    p.add_argument("--salida", default=str(RAIZ / "docs"))
    p.add_argument("--sin-descarga", action="store_true",
                   help="No consulta los feeds; solo regenera la web.")
    p.add_argument("--sin-traduccion", action="store_true",
                   help="No traduce titulares.")
    p.add_argument("--borrador-semanal", action="store_true",
                   help="Escribe el borrador del resumen semanal y termina (no genera la web).")
    p.add_argument("--borrador", default="borrador_semanal.md",
                   help="Archivo de salida del borrador semanal.")
    args = p.parse_args()

    config = cargar_json(Path(args.config), None)
    if not config:
        sys.exit(f"No se encuentra la configuración: {args.config}")
    patrones = preparar_patrones(config)
    ruta_datos = Path(args.datos)
    articulos = cargar_json(ruta_datos, [])

    if not args.sin_descarga:
        print("Descargando feeds…")
        articulos = descargar(config, articulos, patrones)
    articulos = depurar(articulos, config, patrones)
    if args.borrador_semanal:
        escribir_borrador(articulos, config, args.borrador)
        return
    if not args.sin_descarga and not args.sin_traduccion:
        try:
            traducir_titulares(articulos, config)
        except Exception as e:  # la traducción nunca debe impedir que la web se actualice
            print(f"  [AVISO] La traducción falló ({type(e).__name__}: {e}); se sigue sin traducir.")
    if not args.sin_descarga or ruta_datos.exists():
        guardar_datos(ruta_datos, articulos)

    resumenes = cargar_resumenes(Path(args.resumenes))
    Sitio(config, articulos, Path(args.salida), resumenes).generar()
    print(f"Web generada en {args.salida} con {len(articulos)} titulares "
          f"y {len(resumenes)} resúmenes semanales.")


if __name__ == "__main__":
    main()
