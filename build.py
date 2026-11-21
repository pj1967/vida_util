#!/usr/bin/env python3
"""
Vida Útil — generador de la web de noticias.

Qué hace cada vez que se ejecuta:
  1. Lee los feeds RSS definidos en feeds.json.
  2. Añade a data/articulos.json los titulares nuevos (sin duplicados).
  3. Regenera la web completa en la carpeta docs/ (portada, temas y archivo
     por año/mes).

Solo se guardan título, fuente, fecha y enlace a la noticia original.
Uso:  python build.py            (descarga + genera)
      python build.py --sin-descarga   (solo regenera la web con los datos guardados)
"""
import argparse
import hashlib
import html
import json
import re
import shutil
import socket
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser

try:
    from zoneinfo import ZoneInfo
    ZONA = ZoneInfo("Europe/Madrid")
except Exception:  # pragma: no cover
    ZONA = timezone.utc

RAIZ = Path(__file__).resolve().parent
USER_AGENT = "VidaUtil/1.0 (+lector RSS personal)"
MAX_POR_FEED_DEFECTO = 25

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago",
                "sep", "oct", "nov", "dic"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

COLORES = {
    "ia": "#1f4e79",
    "medicina": "#8a1c1c",
    "robotica": "#5b3a8c",
    "programacion": "#0f6b4f",
    "farmacologia": "#a15c00",
    "aeronautica": "#15607a",
    "tecnologia": "#4a4a4a",
}


# ----------------------------------------------------------------- utilidades
def limpiar_texto(s):
    s = html.unescape(s or "")
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def esc(s):
    return html.escape(s or "", quote=True)


def a_local(iso):
    return datetime.fromisoformat(iso).astimezone(ZONA)


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


def descargar(config, articulos):
    socket.setdefaulttimeout(25)
    ahora = datetime.now(timezone.utc)
    conocidos = {a["id"] for a in articulos}
    nuevos_total = 0
    fallos = []

    for feed in config["feeds"]:
        nombre, url, tema = feed["nombre"], feed["url"], feed["tema"]
        palabras = [p.lower() for p in feed.get("palabras", [])]
        maximo = feed.get("max", MAX_POR_FEED_DEFECTO)
        try:
            datos = feedparser.parse(url, agent=USER_AGENT)
        except Exception as e:  # red caída, etc.
            fallos.append(nombre)
            print(f"  [ERROR] {nombre}: {e}")
            continue

        if not datos.entries:
            fallos.append(nombre)
            motivo = getattr(datos, "bozo_exception", "sin entradas")
            print(f"  [AVISO] {nombre}: sin entradas ({motivo})")
            continue

        nuevos = 0
        for e in datos.entries[:maximo]:
            enlace = (e.get("link") or "").strip()
            titulo = limpiar_texto(e.get("title"))
            if not enlace or not titulo:
                continue
            if palabras and not any(p in titulo.lower() for p in palabras):
                continue
            ident = id_articulo(enlace)
            if ident in conocidos:
                continue
            conocidos.add(ident)
            articulos.append({
                "id": ident,
                "titulo": titulo,
                "enlace": enlace,
                "fuente": nombre,
                "tema": tema,
                "fecha": fecha_entrada(e, ahora).isoformat(),
            })
            nuevos += 1
        nuevos_total += nuevos
        print(f"  [OK] {nombre}: {nuevos} nuevos")

    print(f"Total nuevos: {nuevos_total}. Feeds con problemas: {len(fallos)}")
    if fallos:
        print("  -> " + ", ".join(fallos))
    return articulos


# ----------------------------------------------------------------- HTML
CSS = """
:root{--tinta:#1a1a1a;--suave:#5a5a5a;--linea:#d9d9d9;--fondo:#ffffff;--acento:#0b3d6b;--tarjeta:#f6f8fa}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--fondo);color:var(--tinta);
 font:16px/1.5 -apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--acento);text-decoration:none}
a:hover{text-decoration:underline}
.contenedor{max-width:880px;margin:0 auto;padding:0 16px}
header.sitio{border-bottom:3px solid var(--acento);padding:18px 0 10px}
header.sitio h1{margin:0;font:700 1.6rem/1.2 Georgia,"Times New Roman",serif;color:var(--acento)}
header.sitio p{margin:4px 0 10px;color:var(--suave);font-size:.95rem}
nav.menu{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:.95rem}
nav.menu a{padding:4px 0;border-bottom:2px solid transparent}
nav.menu a.activo{border-bottom-color:var(--acento);font-weight:600}
main{padding:18px 0 40px}
h2{font:700 1.25rem/1.3 Georgia,serif;margin:28px 0 8px;padding-left:10px;border-left:5px solid var(--c,var(--acento))}
h2 small{font:400 .85rem sans-serif;color:var(--suave);margin-left:6px}
h3{font-size:1rem;margin:18px 0 4px;color:var(--suave);font-weight:600}
ul.lista{list-style:none;margin:0;padding:0}
li.item{padding:9px 0;border-bottom:1px solid var(--linea)}
li.item a.titular{font-weight:600;color:var(--tinta)}
li.item a.titular:hover{color:var(--acento)}
.meta{display:block;font-size:.82rem;color:var(--suave);margin-top:2px}
.nuevo{display:inline-block;margin-left:6px;padding:0 6px;border:1px solid var(--c,var(--acento));
 border-radius:8px;font-size:.7rem;color:var(--c,var(--acento));font-weight:600}
.etiqueta{color:var(--c,var(--acento));font-weight:600}
.buscador{margin:14px 0 4px}
.buscador input{width:100%;padding:10px 12px;font-size:1rem;border:1px solid var(--linea);border-radius:8px}
.fichas{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:10px;margin:12px 0}
.ficha{display:block;padding:12px;border:1px solid var(--linea);border-left:5px solid var(--c,var(--acento));
 border-radius:8px;background:var(--tarjeta);color:var(--tinta)}
.ficha b{display:block}
.ficha span{color:var(--suave);font-size:.85rem}
.vacio{color:var(--suave);font-style:italic}
footer.pie{border-top:1px solid var(--linea);padding:14px 0 30px;color:var(--suave);font-size:.82rem}
.oculto{display:none!important}
@media print{
 nav.menu,.buscador,footer.pie .no-imprimir{display:none}
 body{font-size:11pt}
 a{color:#000}
 header.sitio{border-bottom:1px solid #000}
 li.item{break-inside:avoid}
}
"""

JS_BUSCADOR = """
<script>
(function(){
  var caja=document.getElementById('buscar'); if(!caja) return;
  caja.addEventListener('input',function(){
    var q=caja.value.toLowerCase().trim();
    document.querySelectorAll('li.item').forEach(function(li){
      li.classList.toggle('oculto', q && li.textContent.toLowerCase().indexOf(q)===-1);
    });
    document.querySelectorAll('section.bloque').forEach(function(s){
      var hay=s.querySelector('li.item:not(.oculto)');
      s.classList.toggle('oculto', q && !hay);
    });
  });
})();
</script>
"""


class Sitio:
    def __init__(self, config, articulos, salida):
        self.cfg = config
        self.temas = config["temas"]
        self.titulo = config["sitio"]["titulo"]
        self.subtitulo = config["sitio"].get("subtitulo", "")
        self.articulos = sorted(articulos, key=lambda a: a["fecha"], reverse=True)
        self.salida = salida
        self.ahora = datetime.now(timezone.utc)
        for a in self.articulos:
            a["_dt"] = a_local(a["fecha"])

    # -- piezas
    def color(self, tema):
        return COLORES.get(tema, "#444444")

    def escribir(self, ruta_rel, contenido):
        ruta = self.salida / ruta_rel
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(contenido, encoding="utf-8")

    def pagina(self, titulo, cuerpo, raiz, activo="", buscador=False):
        enlaces = [("portada", "Portada", f"{raiz}index.html"),
                   ("archivo", "Archivo", f"{raiz}archivo/index.html")]
        for clave, nombre in self.temas.items():
            enlaces.append((clave, nombre, f"{raiz}tema/{clave}.html"))
        menu = "".join(
            f'<a href="{u}"{" class=activo" if k == activo else ""}>{esc(n)}</a>'
            for k, n, u in enlaces)
        caja = ('<div class="buscador"><input id="buscar" type="search" '
                'placeholder="Buscar en los titulares de esta página…" '
                'autocomplete="off"></div>') if buscador else ""
        actualizado = fecha_corta(self.ahora.astimezone(ZONA)) + \
            self.ahora.astimezone(ZONA).strftime(", %H:%M")
        return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(titulo)} · {esc(self.titulo)}</title>
<link rel="stylesheet" href="{raiz}estilo.css">
</head><body>
<header class="sitio"><div class="contenedor">
<h1><a href="{raiz}index.html" style="color:inherit">{esc(self.titulo)}</a></h1>
<p>{esc(self.subtitulo)}</p>
<nav class="menu">{menu}</nav>
</div></header>
<main><div class="contenedor">
{caja}
{cuerpo}
</div></main>
<footer class="pie"><div class="contenedor">
Actualizado automáticamente: {actualizado}. Solo se muestran titulares y enlaces; el contenido
pertenece a cada fuente original.
</div></footer>
{JS_BUSCADOR if buscador else ""}
</body></html>"""

    def item(self, a, con_fecha=True, con_tema=False):
        dt = a["_dt"]
        nuevo = ""
        if self.ahora - datetime.fromisoformat(a["fecha"]) < timedelta(hours=48):
            nuevo = '<span class="nuevo">nuevo</span>'
        partes = []
        if con_tema:
            partes.append(f'<span class="etiqueta" style="--c:{self.color(a["tema"])}">'
                          f'{esc(self.temas.get(a["tema"], a["tema"]))}</span>')
        partes.append(esc(a["fuente"]))
        if con_fecha:
            partes.append(fecha_corta(dt))
        meta = " · ".join(partes)
        return (f'<li class="item" style="--c:{self.color(a["tema"])}">'
                f'<a class="titular" href="{esc(a["enlace"])}" target="_blank" '
                f'rel="noopener noreferrer">{esc(a["titulo"])}</a>'
                f'<span class="meta">{meta}{nuevo}</span></li>')

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

    # -- páginas
    def portada(self):
        dias = self.cfg["sitio"].get("dias_portada", 10)
        maximo = self.cfg["sitio"].get("max_por_tema_portada", 12)
        limite = self.ahora - timedelta(days=dias)
        fichas, bloques = [], []
        for clave, nombre in self.temas.items():
            propios = [a for a in self.articulos if a["tema"] == clave]
            recientes = [a for a in propios
                         if datetime.fromisoformat(a["fecha"]) >= limite][:maximo]
            if len(recientes) < 5:
                recientes = propios[:5]
            fichas.append(
                f'<a class="ficha" style="--c:{self.color(clave)}" href="#{clave}">'
                f'<b>{esc(nombre)}</b><span>{len(propios)} titulares guardados</span></a>')
            if recientes:
                cuerpo = '<ul class="lista">' + "".join(self.item(a) for a in recientes) + "</ul>"
            else:
                cuerpo = '<p class="vacio">Aún no hay noticias de este tema.</p>'
            bloques.append(
                f'<section class="bloque" id="{clave}">'
                f'<h2 style="--c:{self.color(clave)}">{esc(nombre)}'
                f'<small><a href="tema/{clave}.html">ver todas →</a></small></h2>{cuerpo}</section>')
        cuerpo = ('<h2 style="--c:#0b3d6b">Lo más reciente</h2>'
                  f'<div class="fichas">{"".join(fichas)}</div>' + "".join(bloques))
        self.escribir("index.html", self.pagina("Portada", cuerpo, "", "portada", buscador=True))

    def paginas_tema(self):
        for clave, nombre in self.temas.items():
            propios = [a for a in self.articulos if a["tema"] == clave]
            por_mes = defaultdict(list)
            for a in propios:
                por_mes[(a["_dt"].year, a["_dt"].month)].append(a)
            partes = [f'<h2 style="--c:{self.color(clave)}">{esc(nombre)}'
                      f'<small>{len(propios)} titulares</small></h2>']
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
                          self.pagina(nombre, "".join(partes), "../", clave, buscador=True))

    def archivo(self):
        por_mes = defaultdict(list)
        for a in self.articulos:
            por_mes[(a["_dt"].year, a["_dt"].month)].append(a)

        # índice general
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

        # carpeta por mes: índice + una página por tema
        for (y, m), items in por_mes.items():
            carpeta = f"archivo/{y}/{m:02d}"
            raiz = "../../../"
            fichas = []
            for clave, nombre in self.temas.items():
                n = sum(1 for a in items if a["tema"] == clave)
                if n:
                    fichas.append(
                        f'<a class="ficha" style="--c:{self.color(clave)}" '
                        f'href="{clave}.html"><b>{esc(nombre)}</b><span>{n} titulares</span></a>')
                    propios = [a for a in items if a["tema"] == clave]
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

    def generar(self):
        if self.salida.exists():
            shutil.rmtree(self.salida)
        self.salida.mkdir(parents=True)
        self.escribir("estilo.css", CSS)
        self.escribir(".nojekyll", "")
        self.portada()
        self.paginas_tema()
        self.archivo()


# ----------------------------------------------------------------- principal
def main():
    p = argparse.ArgumentParser(description="Genera la web de noticias.")
    p.add_argument("--config", default=str(RAIZ / "feeds.json"))
    p.add_argument("--datos", default=str(RAIZ / "data" / "articulos.json"))
    p.add_argument("--salida", default=str(RAIZ / "docs"))
    p.add_argument("--sin-descarga", action="store_true",
                   help="No consulta los feeds; solo regenera la web.")
    args = p.parse_args()

    config = cargar_json(Path(args.config), None)
    if not config:
        sys.exit(f"No se encuentra la configuración: {args.config}")
    ruta_datos = Path(args.datos)
    articulos = cargar_json(ruta_datos, [])

    if not args.sin_descarga:
        print("Descargando feeds…")
        articulos = descargar(config, articulos)
        guardar_datos(ruta_datos, articulos)

    Sitio(config, articulos, Path(args.salida)).generar()
    print(f"Web generada en {args.salida} con {len(articulos)} titulares.")


if __name__ == "__main__":
    main()
