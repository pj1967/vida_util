# Vida Útil — web de noticias automática

Web estática y gratuita con noticias de **IA, medicina, robótica, programación,
farmacología, aeronáutica y tecnología en general**. Se actualiza sola dos veces al día, muestra lo más
nuevo en la portada y guarda lo antiguo en un archivo ordenado por año y mes.

Solo se guardan **título, fuente, fecha y enlace** a la noticia original (no se
copian ni resumen textos de otros medios).

## Cómo funciona

```
feeds.json ──► build.py ──► data/articulos.json  (historial acumulado)
                       └──► docs/                (la web publicada)
```

- `feeds.json`: lista de fuentes (RSS) y temas. Aquí añades o quitas fuentes.
- `build.py`: descarga los feeds, evita duplicados y genera la web.
- `.github/workflows/actualizar.yml`: lo ejecuta GitHub automáticamente.
- `docs/`: web generada. **No se edita a mano**, se regenera sola.

Estructura de la web generada:

```
docs/
├── index.html                 Portada: lo más reciente de cada tema
├── tema/ia.html …             Todo lo guardado de cada tema, por mes
└── archivo/
    ├── index.html             Años y meses
    └── 2026/11/
        ├── index.html         Todo noviembre 2026, por día
        └── ia.html …          Noviembre 2026 solo de ese tema
```

## Puesta en marcha (una sola vez, ~15 minutos, gratis)

1. Crea una cuenta en <https://github.com> (gratuita).
2. Pulsa **New repository**. Ponle un nombre (por ejemplo `radar-noticias`),
   déjalo **Public** y créalo.
3. En el repositorio nuevo elige **uploading an existing file** y sube todo el
   contenido de esta carpeta (incluida la carpeta oculta `.github`). Si desde el
   móvil no puedes subir carpetas ocultas, hazlo desde un ordenador.
4. Ve a **Settings → Pages**. En *Build and deployment*, elige
   **Deploy from a branch**, rama `main` y carpeta **/docs**. Guarda.
5. Ve a **Actions**, entra en *Actualizar noticias* y pulsa **Run workflow**
   para la primera ejecución (tarda 1–2 minutos).
6. Tu web estará en `https://TU-USUARIO.github.io/NOMBRE-DEL-REPOSITORIO/`
   (GitHub te muestra la dirección en Settings → Pages).

A partir de ahí se actualiza sola cada día. Para forzar una actualización:
Actions → *Actualizar noticias* → *Run workflow*.

## Personalizar

- **Añadir una fuente**: copia una línea de `feeds.json` y cambia nombre, `url`
  y `tema`. Cualquier web con RSS sirve (busca el icono RSS o añade `/feed`).
- **Filtrar una fuente general**: añade `"palabras": ["robot", "drone"]` y solo
  se guardarán titulares que contengan alguna de esas palabras.
- **Limitar una fuente muy activa**: añade `"max": 10` (titulares por ejecución).
- **Añadir un tema nuevo**: añádelo en `"temas"` y úsalo en algún feed.
- **Cuántos días muestra la portada**: `dias_portada` y `max_por_tema_portada`.
- **Cambiar el título de la web**: bloque `"sitio"` de `feeds.json`.

## Probarlo en tu ordenador (opcional)

```bash
pip install -r requirements.txt
python build.py            # descarga y genera
python build.py --sin-descarga   # solo regenera con los datos guardados
```

Abre `docs/index.html` en el navegador.

## Si una fuente deja de funcionar

Algunas webs cambian la dirección de su feed. En el registro de la ejecución
(Actions → última ejecución → *Descargar noticias*) aparece `[AVISO]` junto a la
fuente que falló. Basta con corregir o quitar esa línea en `feeds.json`; el resto
sigue funcionando y el historial no se pierde.

## Nota sobre contenido médico y farmacológico

La web es un agregador de titulares con enlace a la fuente original. No ofrece
consejo médico ni sustituye a profesionales sanitarios.
