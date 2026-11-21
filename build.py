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
MAX_POR_FEED_DEFECTO = 10

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
:root{--tinta:#1b1f24;--suave:#5f6b7a;--linea:#e3e8ee;--fondo:#ffffff;--acento:#0b3d6b;--tarjeta:#f7f9fb}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;scroll-behavior:smooth}
body{margin:0;background:var(--fondo);color:var(--tinta);
 font:16px/1.55 Inter,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--acento);text-decoration:none}
a:hover{text-decoration:underline}
.contenedor{max-width:1040px;margin:0 auto;padding:0 18px}
header.sitio{padding:28px 0 0}
.marca h1{margin:0;font-size:2.1rem;line-height:1.05;font-weight:800;letter-spacing:-.02em}
.marca h1 a{color:var(--tinta);text-decoration:none}
.marca h1 span{color:var(--acento)}
.lema{margin:8px 0 0;font-size:1.08rem;font-weight:600;color:var(--acento)}
.subtitulo{margin:2px 0 0;color:var(--suave);font-size:.95rem}
.autor{margin:8px 0 0;color:var(--suave);font-size:.85rem}
nav.menu{display:flex;gap:8px;overflow-x:auto;padding:18px 0 16px;border-bottom:1px solid var(--linea);scrollbar-width:thin}
nav.menu a{white-space:nowrap;padding:6px 13px;border:1px solid var(--linea);border-radius:999px;
 color:var(--tinta);font-size:.9rem;background:#fff}
nav.menu a:hover{background:var(--tarjeta);text-decoration:none}
nav.menu a.activo{background:#eaf1f8;border-color:#bcd0e4;color:var(--acento);font-weight:600}
main{padding:8px 0 44px}
.intro{margin:24px 0 14px;font-size:1.35rem;font-weight:700;letter-spacing:-.01em}
.intro small{display:block;margin-top:2px;font-size:.88rem;font-weight:400;color:var(--suave)}
.rejilla{display:grid;grid-template-columns:repeat(auto-fill,minmax(310px,1fr));gap:16px}
.tema-card{border:1px solid var(--linea);border-top:4px solid var(--c,var(--acento));border-radius:12px;
 padding:14px 16px 6px;background:#fff;box-shadow:0 1px 3px rgba(16,24,40,.06)}
.tema-card header{display:flex;justify-content:space-between;align-items:baseline;gap:8px;margin-bottom:2px}
.tema-card h2{margin:0;padding:0;border:0;font-size:1.05rem;font-weight:700;color:var(--c,var(--acento))}
.tema-card header a{font-size:.82rem;white-space:nowrap}
h2{font-size:1.25rem;line-height:1.3;font-weight:700;margin:28px 0 8px;padding-left:12px;
 border-left:5px solid var(--c,var(--acento))}
h2 small{font-size:.85rem;font-weight:400;color:var(--suave);margin-left:6px}
h3{font-size:1rem;margin:18px 0 4px;color:var(--suave);font-weight:600}
ul.lista{list-style:none;margin:0;padding:0}
li.item{padding:10px 0;border-bottom:1px solid var(--linea)}
li.item:last-child{border-bottom:0}
li.item a.titular{font-weight:600;color:var(--tinta);line-height:1.35}
li.item a.titular:hover{color:var(--acento)}
.meta{display:block;font-size:.8rem;color:var(--suave);margin-top:3px}
.nuevo{display:inline-block;margin-left:6px;padding:0 7px;border:1px solid var(--c,var(--acento));
 border-radius:8px;font-size:.68rem;color:var(--c,var(--acento));font-weight:600}
.etiqueta{color:var(--c,var(--acento));font-weight:600}
.buscador{margin:16px 0 0}
.buscador input{width:100%;padding:10px 14px;font-size:1rem;border:1px solid var(--linea);border-radius:10px;background:#fff}
.buscador input:focus{outline:2px solid #bcd0e4;border-color:var(--acento)}
.fichas{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:10px;margin:12px 0}
.ficha{display:block;padding:12px 14px;border:1px solid var(--linea);border-left:5px solid var(--c,var(--acento));
 border-radius:10px;background:var(--tarjeta);color:var(--tinta)}
.ficha b{display:block}
.ficha span{color:var(--suave);font-size:.85rem}
.vacio{color:var(--suave);font-style:italic}
main p{max-width:68ch}
footer.pie{border-top:1px solid var(--linea);padding:16px 0 32px;color:var(--suave);font-size:.82rem}
.oculto{display:none!important}
@media (max-width:520px){.marca h1{font-size:1.75rem}.rejilla{grid-template-columns:1fr}}
@media print{
 nav.menu,.buscador{display:none}
 body{font-size:11pt}
 a{color:#000}
 .rejilla{display:block}
 .tema-card{box-shadow:none;break-inside:avoid;margin-bottom:12px}
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
        self.lema = config["sitio"].get("lema", "")
        self.autor = config["sitio"].get("autor", "")
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
        enlaces.append(("acerca", "Acerca de", f"{raiz}acerca.html"))
        menu = "".join(
            f'<a href="{u}"{" class=activo" if k == activo else ""}>{esc(n)}</a>'
            for k, n, u in enlaces)
        caja = ('<div class="buscador"><input id="buscar" type="search" '
                'placeholder="Buscar en los titulares de esta página…" '
                'autocomplete="off"></div>') if buscador else ""
        partes = self.titulo.rsplit(" ", 1)
        marca = (f'{esc(partes[0])} <span>{esc(partes[1])}</span>'
                 if len(partes) == 2 else esc(self.titulo))
        lema = f'<p class="lema">{esc(self.lema)}</p>' if self.lema else ""
        sub = f'<p class="subtitulo">{esc(self.subtitulo)}</p>' if self.subtitulo else ""
        autor = f'<p class="autor">por {esc(self.autor)}</p>' if self.autor else ""
        ahora_l = self.ahora.astimezone(ZONA)
        actualizado = fecha_corta(ahora_l) + ahora_l.strftime(", %H:%M")
        pie_autor = f"{esc(self.titulo)} · {esc(self.autor)} · " if self.autor else ""
        return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(titulo)} · {esc(self.titulo)}</title>
<link rel="stylesheet" href="{raiz}estilo.css">
</head><body>
<header class="sitio"><div class="contenedor">
<div class="marca"><h1><a href="{raiz}index.html">{marca}</a></h1></div>
{lema}{sub}{autor}
<nav class="menu">{menu}</nav>
</div></header>
<main><div class="contenedor">
{caja}
{cuerpo}
</div></main>
<footer class="pie"><div class="contenedor">
{pie_autor}Actualizado automáticamente: {actualizado}. Solo se muestran titulares y enlaces; el contenido
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
    def seleccion_portada(self, propios, dias, maximo, max_fuente):
        """Las más recientes del tema, con tope por fuente para que haya variedad."""
        limite = self.ahora - timedelta(days=dias)
        elegidos, por_fuente = [], defaultdict(int)
        for a in propios:  # ya vienen ordenadas de más nueva a más antigua
            if datetime.fromisoformat(a["fecha"]) < limite:
                break
            if por_fuente[a["fuente"]] >= max_fuente:
                continue
            elegidos.append(a)
            por_fuente[a["fuente"]] += 1
            if len(elegidos) >= maximo:
                break
        if len(elegidos) < 3:  # pocas recientes: completar con lo último guardado
            for a in propios:
                if a not in elegidos:
                    elegidos.append(a)
                if len(elegidos) >= 3:
                    break
        return elegidos

    def portada(self):
        sitio = self.cfg["sitio"]
        dias = sitio.get("dias_portada", 7)
        maximo = sitio.get("max_por_tema_portada", 5)
        max_fuente = sitio.get("max_por_fuente_portada", 2)
        tarjetas = []
        for clave, nombre in self.temas.items():
            propios = [a for a in self.articulos if a["tema"] == clave]
            elegidos = self.seleccion_portada(propios, dias, maximo, max_fuente)
            if elegidos:
                lista = ('<ul class="lista">'
                         + "".join(self.item(a) for a in elegidos) + "</ul>")
            else:
                lista = '<p class="vacio">Aún no hay noticias de este tema.</p>'
            tarjetas.append(
                f'<section class="tema-card bloque" id="{clave}" style="--c:{self.color(clave)}">'
                f'<header><h2>{esc(nombre)}</h2>'
                f'<a href="tema/{clave}.html">Ver todas ({len(propios)}) →</a></header>'
                f'{lista}</section>')
        cuerpo = ('<div class="intro">Lo más reciente'
                  '<small>Selección automática: pocas noticias por tema y de fuentes variadas.'
                  '</small></div><div class="rejilla">' + "".join(tarjetas) + "</div>")
        self.escribir("index.html", self.pagina("Portada", cuerpo, "", "portada", buscador=True))

    def acerca(self):
        textos = self.cfg["sitio"].get("acerca") or [
            "Aprendo y comparto, en castellano, cómo se aplican los datos y la inteligencia "
            "artificial al mantenimiento y a la ingeniería."]
        cuerpo = "<h2>Acerca de</h2>" + "".join(f"<p>{esc(t)}</p>" for t in textos)
        self.escribir("acerca.html", self.pagina("Acerca de", cuerpo, "", "acerca"))

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
        self.acerca()
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
