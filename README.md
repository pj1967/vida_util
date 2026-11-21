# Mente Máquina — proyectos y noticias de IA, robótica y automatización

Blog sobre **inteligencia artificial, robótica y automatización** en distintos ámbitos
(IA, robótica, programación, aeronáutica y otros: industria, agricultura, clima, energía,
salud y farmacia). Se actualiza solo y solo muestra titulares con enlace a la fuente original.

## Cómo funciona

```
feeds.json ──► build.py ──► data/articulos.json   (historial de titulares)
data/resumenes/*.json ─┘└──► docs/                 (la web publicada)
```

- `feeds.json`: temas, fuentes (RSS), palabras de relevancia, proyectos y retos.
- `build.py`: descarga los feeds, **descarta lo que no tiene que ver con IA, robótica o
  automatización**, clasifica por tema y genera la web.
- `.github/workflows/actualizar.yml`: GitHub lo ejecuta solo, dos veces al día.
- `docs/`: web generada. No se edita a mano.
- `data/resumenes/`: un archivo por semana con los resúmenes por tema (los escribes tú).

## Qué entra y qué no

Cada fuente tiene un campo `"tema"` y, a veces, `"filtrar": true`.

- **Fuente especializada** (por ejemplo «The Robot Report»): entra todo, con su tema fijo.
- **Fuente con `"filtrar": true`**: solo entra lo que contiene alguna palabra de la lista
  `relevancia` de `feeds.json`.
- **`"tema": "auto"`** (fuentes generales como Xataka o Genbeta): además del filtro, el tema
  se elige con las reglas de `clasificacion` (robótica, aeronáutica, programación, otros;
  si no encaja en ninguna, inteligencia artificial).

En el registro de cada ejecución verás cuántos titulares se descartaron por fuente. Si se
cuela algo que no toca, o se pierde algo bueno, se ajusta la lista de palabras.

## Resúmenes semanales

Crea un archivo `data/resumenes/AAAA-MM-DD.json` (fecha del lunes) con este formato:

```json
{
  "desde": "2026-11-16",
  "hasta": "2026-11-22",
  "temas": {
    "ia": {
      "resumen": "Texto del resumen en castellano.",
      "fuentes": [
        {"fuente": "Nombre del medio", "enlace": "https://..."}
      ]
    }
  }
}
```

Para crearlo directamente en GitHub, abre (cambiando la fecha):
`https://github.com/pj1967/vida_util/new/main?filename=data/resumenes/2026-11-16.json`

Los temas sin resumen muestran sus últimos titulares. El resumen más reciente va en la
portada y todos quedan en la página «Resúmenes».

## Contador de visitas y comentarios

- **Visitas** (privadas, sin cookies): crea una cuenta gratuita en goatcounter.com, elige
  un código y escríbelo en `"goatcounter"` dentro de `"sitio"` en `feeds.json`.
- **Comentarios**: crea un formulario (por ejemplo, Google Forms) y pega su dirección
  `https://...` en `"formulario"`. Aparecerán «Contacto» en el menú y «Enviar comentario»
  en el pie, sin mostrar tu correo.

## Proyectos (lo principal de la web) y retos

Cada proyecto de la lista `"proyectos"` de `feeds.json` genera su tarjeta en la portada
(«Aprende haciendo») y su propia ficha en `proyectos/<id>.html`. Campos: `id`, `titulo`,
`estado` (`proximo`, `idea`, `curso`, `publicado`), `nivel` (inicial, intermedio, avanzado),
`area`, `descripcion`, `dataset` (`nombre`, `url`), `objetivo`, `datos`, `herramientas`,
`metodo`, `metrica`, `pasos` (cada uno con `titulo`, `que`, `como`, `porque`, `para`),
`resultados`, `limitaciones`, `codigo` (enlace) y `entrega` (`notebook`, `repositorio`,
`demo`, `articulo`: enlaces, vacío = «pendiente»). Con `noticias_palabras` la ficha enseña
automáticamente las noticias relacionadas.

Los retos están en `"retos"`.

## Traducción, repetidos y filtros

- Los titulares en inglés se traducen solos (Argos Translate, opcional: `requirements-traduccion.txt`).
  Si falla, se muestra el original.
- Titulares casi idénticos de medios distintos se unen en uno («También en: …»).
- En la portada, máximo 4 titulares por medio y día (`max_por_fuente_dia` en `sitio`).
- Filtros de tiempo: últimas 24 horas, esta semana, este mes.
- Clasificación por prioridad: robots/drones primero, luego IA (LLM, GPT…), aeronáutica,
  programación, otros y, al final, automatización general.

## Borrador semanal

Cada lunes el workflow crea un *Issue* con el borrador; GitHub te avisa por correo. Pégalo en
el chat para obtener el resumen en castellano y súbelo como `data/resumenes/AAAA-MM-DD.json`.

## Probarlo en el ordenador (opcional)

```bash
pip install -r requirements.txt
python build.py
python build.py --sin-descarga   # solo regenera con lo guardado
```

Abre `docs/index.html` en el navegador.

## Si una fuente deja de funcionar

En el registro de la ejecución (Actions → última ejecución → «Descargar noticias») aparece
`[AVISO]` junto a la fuente que falló. Corrige o quita esa línea en `feeds.json`; el resto
sigue funcionando y el historial no se pierde.

## Nota

Contenido divulgativo: no sustituye el consejo médico ni profesional. Los datos de cada
proyecto se citan con su fuente y sus límites.
