# quinzemin — Documentación técnica completa

> Documento de referencia para la redacción de la memoria del TFM.  
> Describe el estado actual del sistema (agosto 2026), incluyendo el módulo GTFS,  
> la parametrización completa vía `config.yaml` y el formulario web `configurar.html`.

---

## 1. Objetivo y marco conceptual

**quinzemin** (catalán: "quince minutos") es una herramienta de análisis y visualización de accesibilidad urbana basada en el modelo de la **ciudad de los 15 minutos** (*15-minute city*), propuesto por Carlos Moreno y adoptado como marco de política urbana por ciudades como París o Barcelona.

El concepto central es que cualquier residente urbano debería poder acceder a pie o en transporte público a un conjunto de servicios esenciales (salud, educación, alimentación, espacios verdes, cultura, transporte) en un máximo de 15 minutos desde su domicilio. La herramienta operacionaliza este concepto calculando, para cada **sección censal** de una ciudad, cuántos de los servicios configurados son accesibles dentro del umbral definido, y lo representa en un mapa interactivo coroplético.

El sistema tiene dos modos de análisis:

- **Modo distancia** (`distance`): distancia euclídea en línea recta desde el centroide de cada sección censal hasta el elemento más próximo de cada servicio. Umbral configurable en metros (por defecto 1 000 m).
- **Modo tránsito** (`transit`): isócrona real por transporte público usando datos GTFS. Umbral configurable en minutos (por defecto 15 min), con tiempo de paseo a pie hasta/desde las paradas.

El prototipo está implementado para **Valencia (España)** con 7 servicios analizados, pero es completamente parametrizable para cualquier ciudad mediante un fichero `config.yaml` o mediante el formulario web `docs/configurar.html`.

---

## 2. Arquitectura general

### 2.1 Pipeline de ejecución

```
config.yaml
    │
    ├─→ src/download_data.py  →  data/*.geojson  +  data/gtfs_{id}.zip
    │                                │
    └─→ src/main.py  ←──────────────┘
            │
            └─→ docs/index.html       (mapa de accesibilidad, modo distance o transit)

    (paralelo, opcional)
    src/map_gtfs.py  →  docs/mapa_gtfs.html   (visualización de isócronas GTFS)
```

### 2.2 Estructura de ficheros

```
quinzemin/
├── config.yaml                  # Configuración principal (única fuente de verdad)
├── requirements.txt             # Dependencias Python
├── README.md                    # Atribuciones y uso rápido
├── DOCUMENTACIO.md              # Documentación técnica v1 (catalán, TFM)
├── TECHNICAL_DOC.md             # Este fichero
├── src/
│   ├── config.py                # Carga config.yaml → dict Python
│   ├── download_data.py         # Descarga datos desde APIs y portales open data
│   ├── main.py                  # Análisis geoespacial + generación del mapa principal
│   ├── gtfs.py                  # Motor de accesibilidad por transporte público (GTFS)
│   └── map_gtfs.py              # Script de visualización de isócronas GTFS
├── data/                        # Datos descargados (gitignored, regenerar con download_data.py)
│   ├── areas.geojson            # Secciones censales
│   ├── salud.geojson
│   ├── primaria.geojson
│   ├── secundaria.geojson
│   ├── transporte.geojson
│   ├── supermercados.geojson
│   ├── zonas_verdes.geojson
│   ├── cultura.geojson
│   ├── gtfs_metro.zip           # Feed GTFS Metrovalencia (si configurado)
│   └── gtfs_emt.zip             # Feed GTFS EMT Valencia (si configurado)
└── docs/
    ├── index.html               # Mapa principal (salida de main.py, publicado en GitHub Pages)
    ├── mapa_gtfs.html           # Mapa de isócronas (salida de map_gtfs.py)
    └── configurar.html          # Formulario web de configuración (estático, GitHub Pages)
```

### 2.3 Dependencias Python

```
numpy       — soporte numérico (dependencia de geopandas)
pandas      — manipulación de datos tabulares
geopandas   — análisis geoespacial (geometrías, proyecciones, distancias)
folium      — generación de mapas interactivos HTML (wrapper Python de Leaflet.js)
matplotlib  — paleta de colores (gradiente RdYlGn para el mapa coroplético)
pyyaml      — lectura de config.yaml
requests    — descarga HTTP de datos
urllib3     — gestión de SSL (incluido con requests)
```

Dependencias implícitas (instaladas con geopandas): `shapely`, `pyproj`, `fiona`.

---

## 3. Parametrización: `config.yaml`

`config.yaml` es la única fuente de verdad del sistema. `src/config.py` lo lee como un dict Python plano con `yaml.safe_load()`. Todos los scripts importan `config.load()` para acceder a él.

### 3.1 Sección `city`

```yaml
city:
  name: "Valencia"
  center: [39.4699, -0.3763]   # [lat, lon] del centro del mapa inicial
  zoom: 12                     # nivel de zoom inicial de Leaflet
  bbox: "39.38,-0.45,39.55,-0.29"  # bounding box S,W,N,E para consultas Overpass

  areas:
    url: "https://..."         # URL del GeoJSON de secciones censales (o unidades de análisis)
    id_field: "coddistsecc"   # campo del GeoJSON que identifica unívocamente cada área
```

- **`center` / `zoom`**: inicializan el mapa Folium/Leaflet.
- **`bbox`**: usado exclusivamente en las consultas Overpass QL para servicios de tipo `overpass`, como placeholder `{bbox}`. Formato: `"S,W,N,E"` (latitud mínima, longitud mínima, latitud máxima, longitud máxima).
- **`areas.url`**: puede apuntar a cualquier portal GeoJSON accesible por HTTP. Para Valencia apunta al Geoportal municipal (capa de secciones censales del padrón, 680 secciones).
- **`areas.id_field`**: nombre del campo que se usa como etiqueta en el tooltip del mapa. Para Valencia es `coddistsecc` (código de distrito-sección del INE).

### 3.2 Sección `analysis`

```yaml
analysis:
  mode: distance         # "distance" | "transit"
  distance_m: 1000       # umbral en metros (modo distance)
  time_minutes: 15       # presupuesto total de viaje en minutos (modo transit)
  walking_speed_mpm: 80  # velocidad a pie en metros/minuto (~4,8 km/h)
  max_walk_to_stop_m: 500  # distancia máxima a pie hasta/desde una parada GTFS
  gtfs_sources:          # lista de feeds GTFS (vacío = sin GTFS)
    - id: metro
      label: "Metrovalencia (FGV)"
      url: "http://www.metrovalencia.es/google_transit_feed/google_transit.zip"
      verify_ssl: false   # false para servidores con certificados FNMT/GVA
    - id: emt
      label: "EMT Valencia (autobuses urbanos)"
      url: "https://opendata.vlci.valencia.es/dataset/.../download/google_transit2026-05-31.zip"
```

- **`mode: distance`** (por defecto): usa distancia euclídea. No requiere datos GTFS.
- **`mode: transit`**: activa el motor GTFS en `main.py`. Requiere feeds descargados.
- **`distance_m`**: umbral de accesibilidad en modo distancia. Admite override por servicio individual (campo `distance_m` en cada servicio).
- **`time_minutes`**: presupuesto total de viaje (tiempo de paseo + espera en parada + tiempo en vehículo + paseo final).
- **`walking_speed_mpm`**: velocidad peatonal. 80 m/min equivale a ~4,8 km/h (velocidad estándar de planificación urbana).
- **`max_walk_to_stop_m`**: radio máximo de búsqueda de paradas desde el centroide y desde el destino. Limita el primer y último tramo a pie.
- **`gtfs_sources`**: lista. Cada fuente se descarga a `data/gtfs_{id}.zip`. Múltiples fuentes se combinan en un único grafo (los `stop_id` se prefiján con `{id}_` para evitar colisiones entre redes).
- **`verify_ssl`**: `false` desactiva la verificación del certificado TLS. Necesario para algunos portales de la Generalitat Valenciana que usan certificados FNMT no incluidos en el bundle de Python/certifi.

### 3.3 Sección `map`

```yaml
map:
  emoji_min_zoom: 14   # zoom mínimo de Leaflet a partir del cual aparecen emojis
```

- **`emoji_min_zoom`**: los marcadores de emoji (servicios faltantes) se ocultan por debajo de este nivel de zoom mediante un event listener JavaScript (`map.on('zoomend', fn)`).

### 3.4 Sección `services`

Lista de servicios a analizar. Cada elemento es un dict con los campos siguientes:

```yaml
services:
  - id: salud                  # identificador único, snake_case
    label: "Centros de Salud"  # etiqueta legible para leyenda y tooltip
    emoji: "🏥"               # emoji representativo (opcional)
    url: "https://..."         # URL de descarga directa del GeoJSON
    name_field: "cen_desclar"  # campo del GeoJSON con el nombre del elemento

  - id: primaria
    label: "Ed. Primaria"
    emoji: "🏫"
    url: "https://..."         # mismo GeoJSON que secundaria
    name_field: "dlibre"
    filter:                    # filtro opcional
      field: "dgenerica"       # campo sobre el que filtrar
      contains: "PRIMÀR"       # subcadena (case-insensitive)

  - id: supermercados
    label: "Supermercados"
    emoji: "🛒"
    type: overpass             # fuente Overpass (OpenStreetMap)
    overpass_query: '(nwr["shop"="supermarket"]({bbox});); out center;'
    name_field: "name"

  - id: cultura
    label: "Cultura"
    emoji: "🎭"
    type: overpass
    overpass_query: '(nwr["amenity"="library"]({bbox});nwr["amenity"="theatre"]({bbox});nwr["amenity"="cinema"]({bbox});nwr["amenity"="arts_centre"]({bbox});); out center;'
    name_field: "name"
```

**Campos por servicio:**

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | string, obligatorio | Identificador único. Se usa para nombrar el fichero de datos (`data/{id}.geojson`) y las columnas del GeoDataFrame. |
| `label` | string, obligatorio | Etiqueta visible en la leyenda y los tooltips del mapa. |
| `emoji` | string, opcional | Emoji de 1–2 caracteres que se muestra sobre el centroide de cada área cuando le falta ese servicio (visible solo desde `emoji_min_zoom`). |
| `type` | string, opcional | `"url"` (por defecto) o `"overpass"`. |
| `url` | string | URL de descarga directa del GeoJSON (cuando `type: url`). |
| `overpass_query` | string | Query Overpass QL con `{bbox}` como placeholder (cuando `type: overpass`). |
| `name_field` | string | Campo del GeoJSON que contiene el nombre del elemento, mostrado en el tooltip como "más cercano". |
| `filter.field` | string, opcional | Campo del GeoJSON por el que filtrar filas. |
| `filter.contains` | string, opcional | Subcadena que debe contener el campo (búsqueda case-insensitive con `str.contains`). Permite usar el mismo GeoJSON para varios servicios (p. ej. centros educativos → primaria / secundaria). |
| `distance_m` | int, opcional | Umbral de accesibilidad específico para este servicio, en metros (sobreescribe `analysis.distance_m`). Solo aplica en modo `distance`. |

**Servicios configurados para Valencia (2026):**

| id | Servicio | Fuente | Tipo |
|---|---|---|---|
| `salud` | Centros de Salud | ICV/GVA (WFS) | url |
| `primaria` | Ed. Primaria | VLCi OpenData | url + filtro |
| `secundaria` | Ed. Secundaria | VLCi OpenData | url + filtro |
| `transporte` | Paradas de bus EMT | Geoportal Valencia | url |
| `supermercados` | Supermercados | OpenStreetMap/Overpass | overpass |
| `zonas_verdes` | Parques y jardines | Geoportal Valencia | url |
| `cultura` | Bibliotecas, teatros, cines, centros culturales | OpenStreetMap/Overpass | overpass |

---

## 4. Scripts Python

### 4.1 `src/config.py`

Módulo mínimo. Expone una única función:

```python
def load() -> dict:
    with open(_CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)
```

`_CONFIG_PATH` apunta a `config.yaml` en la raíz del proyecto, relativo a la ubicación del módulo. El dict devuelto refleja la estructura YAML exacta.

---

### 4.2 `src/download_data.py`

Descarga todos los datos externos necesarios y los guarda en `data/`. Diseño tolerante a fallos: cada descarga es independiente (un error no cancela las demás).

**Tipos de descarga implementados:**

1. **Descarga directa HTTP** (`_download_url`): `requests.get()` con streaming y timeout de 60s. Acepta parámetro `verify=False` (con supresión de `InsecureRequestWarning`) para portales con certificados FNMT.

2. **Overpass API** (`_download_overpass`): envía la query al API de Overpass con formato JSON y convierte la respuesta al formato GeoJSON estándar mediante `_osm_to_geojson()`. Implementa fallback entre 3 mirrors públicos (`overpass-api.de`, `overpass.kumi.systems`, `maps.mail.ru`) para tolerancia a fallos.

3. **Overpass a GeoJSON** (`_osm_to_geojson`): convierte elementos OSM de tipo `node` (lat/lon directos) y `way`/`relation` (con `out center;`, que devuelve el centroide geométrico) a features GeoJSON de tipo Point. Los tags OSM se mapean como propiedades.

**Optimización de duplicados:** si dos servicios apuntan a la misma URL (p. ej. primaria y secundaria usan el mismo GeoJSON de centros educativos), el fichero solo se descarga una vez y se copia localmente.

**Descarga GTFS:** siempre que `gtfs_sources` no esté vacío, independientemente del modo de análisis. Cada fuente se descarga a `data/gtfs_{id}.zip`.

---

### 4.3 `src/main.py`

Script principal. Genera `docs/index.html`.

**Pipeline:**

1. **Carga de configuración**: `config.load()` → lectura de parámetros globales y lista de servicios.

2. **Carga de áreas**: lee `data/areas.geojson` con GeoPandas. Reprojecta automáticamente al sistema de referencia UTM óptimo para la ciudad usando `areas.estimate_utm_crs()` (devuelve el EPSG de la zona UTM correspondiente basándose en la extensión geográfica del dataset). Esto evita hardcodear proyecciones y hace el sistema funcional para cualquier ciudad.

3. **Cómputo de centroides**: `areas.geometry.centroid` en coordenadas UTM (metros reales). Estos centroides se usan para medir la distancia desde cada sección censal a los servicios.

4. **Bucle de servicios**: para cada servicio:
   - Lee `data/{id}.geojson` y reprojecta a UTM.
   - Aplica filtro si está configurado.
   - En **modo distance**: `_nearest(centroid, gdf, name_col)` → distancia y nombre del elemento más próximo.
   - Genera columnas por servicio: `dist_{id}_m`, `nombre_{id}`, `{id}_ok`.
   - Acumula en `areas["score"]`.

5. **Función `_nearest`**: calcula la distancia de un punto a todos los elementos de un GeoDataFrame (`gdf.geometry.distance(centroid)`), devuelve la mínima y el nombre del elemento más próximo. Para geometrías poligonales (p. ej. zonas verdes), `distance()` devuelve 0 si el centroide está dentro del polígono, y la distancia al borde más próximo si está fuera.

6. **Función `_score_color`**: mapea el score (0…N_servicios) a un color hex del gradiente **RdYlGn** de matplotlib. El gradiente va de rojo (score=0, sin servicios) a verde (score=N, todos los servicios).

7. **Renderizado del mapa Folium:**
   - Capa `GeoJson` con `style_function` que aplica el color del score por feature.
   - `GeoJsonTooltip` con todos los campos por sección: área, score, y para cada servicio: accesible (booleano), nombre del más próximo, distancia.
   - Capa de emojis (`FeatureGroup`, show=True): un `DivIcon` por sección censal con los emojis de los servicios **faltantes**. Un script JavaScript oculta/muestra la capa según el nivel de zoom actual (`map.on('zoomend', fn)`), con llamada directa e inmediata para el estado inicial.
   - Leyenda fija (`position:fixed`) con escala de colores (gradiente de scores) y lista de emojis por servicio.
   - Enlace fijo a `configurar.html`.

8. **Abre el mapa** en el navegador con `webbrowser.open()`.

**Nota sobre el modo transit en `main.py`**: el modo `transit` está diseñado e implementado en `gtfs.py` pero aún no está integrado en el bucle principal de `main.py` (que actualmente solo implementa el modo `distance`). La integración es el próximo paso de desarrollo. El script `map_gtfs.py` ya usa el motor GTFS para la visualización de isócronas.

---

## 5. Módulo GTFS: `src/gtfs.py`

### 5.1 Motivación y modelo conceptual

El modo de distancia euclídea sobreestima la accesibilidad real: una sección censal puede tener un hospital a 900 m en línea recta pero separada por una autopista o un río, haciendo el trayecto real de 2 km. El módulo GTFS corrige esto usando la **red real de transporte público** como medio de acceso.

El modelo adoptado es **frequency-based** (basado en frecuencia), independiente del horario de salida. En lugar de simular un viaje a hora concreta (p. ej. "salgo a las 8:30"), calcula el **tiempo de viaje típico esperado** para cualquier hora del día, usando el número de expediciones como proxy de la frecuencia:

```
espera_esperada = (16 h de servicio / expediciones_día) / 2
```

Este modelo es adecuado para estudios de planificación urbana de accesibilidad media, donde interesa el comportamiento típico y no el óptimo instantáneo.

### 5.2 Fuentes GTFS: formato y ficheros usados

**GTFS** (General Transit Feed Specification) es el estándar abierto para datos de transporte público, mantenido por MobilityData y adoptado globalmente. Un feed GTFS es un fichero ZIP que contiene archivos CSV con esquema fijo.

Ficheros GTFS utilizados por quinzemin:

| Fichero | Campos usados | Descripción |
|---|---|---|
| `stops.txt` | `stop_id`, `stop_lat`, `stop_lon`, `stop_name` | Ubicación geográfica de cada parada |
| `stop_times.txt` | `trip_id`, `stop_id`, `stop_sequence`, `arrival_time`, `departure_time` | Horarios de paso por cada parada en cada viaje |

Ficheros GTFS no utilizados (presentes en los feeds pero ignorados):
- `routes.txt`, `trips.txt`, `calendar.txt`, `shapes.txt`, etc.

### 5.3 Construcción del grafo de tránsito

`TransitGraph.load(sources, utm_crs)` construye el grafo desde una lista de fuentes:

**Paso 1 — Carga y namespacing:**
Cada feed GTFS se carga por separado. Para evitar colisiones de IDs entre redes distintas (EMT y Metrovalencia pueden tener paradas con el mismo `stop_id` numérico), todos los `stop_id` y `trip_id` se prefiján con `{id}_`:

```
parada "1" de metro → "metro_1"
parada "1" de EMT   → "emt_1"
```

Los dataframes de paradas y horarios de todas las fuentes se concatenan en un único dataframe.

**Paso 2 — Geometría UTM:**
Las coordenadas lat/lon de `stops.txt` se proyectan al CRS UTM de la ciudad (el mismo que usa `main.py`). Esto permite calcular distancias en metros de forma precisa.

**Paso 3 — Construcción del grafo dirigido:**
Se itera sobre `stop_times.txt` agrupado por `trip_id`. Para cada viaje, se crean aristas dirigidas entre paradas consecutivas:

```
arista(stop_a → stop_b) = tiempo_llegada[b] - tiempo_salida[a]  (en segundos)
```

Filtro de sanidad: solo aristas con `0 < tiempo_viaje ≤ 3600 s` (un trayecto entre dos paradas consecutivas no puede exceder 1 hora). Nota: los tiempos en GTFS pueden superar `24:00:00` para viajes nocturnos (p. ej. `25:30:00` significa las 01:30 del día siguiente); el parser `_parse_hms()` lo gestiona correctamente.

**Paso 4 — Tiempos de espera por parada:**
Para cada parada, se cuenta el número de expediciones distintas que la sirven (`n_trips`). El tiempo de espera esperado se estima como:

```
espera_media = max(30s, 16h × 3600s / (2 × n_trips))
```

El factor 2 es el denominador del headway/2. El límite inferior de 30 s evita tiempos de espera irrealistas para paradas muy servidas.

**Paso 5 — Índice espacial STRtree:**
Se construye un `shapely.STRtree` sobre las geometrías UTM de todas las paradas. Permite consultas espaciales de paradas dentro de un radio dado en O(log n).

### 5.4 Algoritmo de accesibilidad: Dijkstra frequency-based

`reachable_from(centroid, budget_s, walk_mps, max_walk_m)` → `{stop_id: time_spent_s}`

```
1. Consulta espacial: paradas dentro de max_walk_m del centroide censal (STRtree).
2. Para cada parada cercana:
     tiempo_paseo = distancia_euclidea / velocidad_peatonal
     tiempo_total_inicial = tiempo_paseo + espera_media_parada
     Si tiempo_total_inicial < budget_s: añadir a cola de prioridad (min-heap).
3. Dijkstra:
     Mientras la cola no esté vacía:
         Extraer parada con menor tiempo gastado.
         Si ya visitada: ignorar.
         Marcar como visitada: best[stop_id] = tiempo_gastado.
         Para cada arista saliente (vecino, tiempo_viaje):
             nuevo_tiempo = tiempo_gastado + tiempo_viaje
             (sin espera adicional: el usuario ya está en el vehículo)
             Si nuevo_tiempo < budget_s y vecino no visitado:
                 añadir a cola.
4. Devolver best: dict de paradas alcanzables con el tiempo gastado para llegar.
```

La ausencia de espera adicional en los trasbordos es una simplificación que infravalora ligeramente el tiempo real, pero es coherente con el modelo frequency-based (el tiempo de espera ya fue contabilizado al embarcar en origen).

### 5.5 Comprobación de accesibilidad a un servicio

`service_min_time(reachable, service_gdf, name_col, walk_mps, budget_s, max_walk_m)` → `(tiempo_s | None, nombre)`

Para cada elemento del GeoDataFrame del servicio:
1. Encuentra las paradas a menos de `max_walk_m` del elemento (STRtree).
2. Para cada parada alcanzable (`stop_id in reachable`): calcula `tiempo_total = reachable[stop_id] + distancia_a_servicio / walk_mps`.
3. Si `tiempo_total ≤ budget_s`: el servicio es accesible desde ese centroide.
4. Devuelve el tiempo mínimo y el nombre del servicio más próximo.

Para geometrías poligonales (p. ej. parques): `geom.distance(stop_geom)` devuelve 0 si la parada está dentro del polígono, lo que es correcto (si hay una parada dentro del parque, el paseo final es 0).

### 5.6 Visualización de isócronas: `reachable_hull`

`reachable_hull(reachable, buffer_m=150)` → polígono shapely o None

Calcula el **casco convexo** de todas las paradas alcanzables desde un centroide, ampliado con un buffer de 150 m. El resultado es una aproximación de la "isócrona de transporte público" para esa sección censal.

Cuando se superponen las isócronas de todas las secciones censales con baja opacidad (0.12), las zonas con mejor cobertura de transporte aparecen visualmente más densas, creando un efecto de mapa de calor.

### 5.7 Fuentes GTFS configuradas para Valencia

| Red | Publicador | URL directa | Verificación SSL |
|---|---|---|---|
| Metrovalencia (metro L1–L10, tranvía T) | FGV — Ferrocarrils de la Generalitat Valenciana | `http://www.metrovalencia.es/google_transit_feed/google_transit.zip` | `verify_ssl: false` (cert FNMT) |
| EMT Valencia (49 líneas de bus, 1155 paradas) | EMT — Ajuntament de València | `https://opendata.vlci.valencia.es/dataset/.../google_transit2026-05-31.zip` | Por defecto (cert válido) |

**Nota sobre Valenbisi**: el sistema de bicicletas compartidas de Valencia publica datos en formato **GBFS** (General Bikeshare Feed Specification), no GTFS. GBFS proporciona disponibilidad en tiempo real de estaciones (número de bicis y anclajes libres), sin información de rutas ni horarios. No es integrable en el motor GTFS de quinzemin. Una posible extensión futura sería modelar la accesibilidad en bicicleta con radio de influencia (p. ej. 3 km en 15 min a 12 km/h) como capa adicional.

---

## 6. Script de visualización GTFS: `src/map_gtfs.py`

Script independiente de `main.py`. Genera `docs/mapa_gtfs.html`.

**Funcionamiento:**

1. Lee config.yaml y construye la lista de fuentes GTFS disponibles (las que tienen `data/gtfs_{id}.zip` descargado).
2. Carga áreas censales, estima UTM, carga `TransitGraph`.
3. Para cada centroide censal: ejecuta `reachable_from()` y `reachable_hull()`.
4. Acumula en `reach_count[stop_id]` cuántas áreas pueden alcanzar cada parada.
5. Genera mapa Folium con tres capas:
   - **Secciones censales** (contornos grises, siempre visible).
   - **Isócronas** (polígonos azules semitransparentes, efecto heatmap acumulativo, siempre visible).
   - **Paradas GTFS** (CircleMarkers coloreados con gradiente YlOrRd según `reach_count`, desactivada por defecto).
6. Añade leyenda con conteo de fuentes, paradas y cobertura (% de secciones con al menos una parada alcanzable).

**No requiere que `analysis.mode` sea `transit`** — funciona independientemente del modo de análisis de `main.py`.

---

## 7. Formulario web: `docs/configurar.html`

Página HTML estática completamente autocontenida (CSS + JS inline). No requiere servidor. Publicada en GitHub Pages junto con el mapa principal.

### 7.1 Objetivo

Permite a cualquier usuario (sin conocimientos de programación ni acceso al servidor) generar un `config.yaml` válido para analizar su propia ciudad, sin editar código. El YAML generado puede descargarse, colocarse en la raíz del proyecto y ejecutar el pipeline Python.

### 7.2 Tecnología

- **js-yaml 4.1.0** (CDN: `cdnjs.cloudflare.com`): serialización del objeto JavaScript de configuración a YAML canónico con comillas y sangría correctas.
- **Nominatim** (API pública de OpenStreetMap): autocompletado de ciudades por nombre.
- Sin frameworks (Vanilla JS), sin dependencias locales.

### 7.3 Secciones del formulario

**Sección 1 — Ciudad:**
- Campo de texto "Nombre de la ciudad" con autocompletado Nominatim:
  - Debounce de 500 ms para no saturar la API.
  - Al seleccionar una sugerencia, rellena automáticamente: lat/lon (del resultado), bbox (convirtiendo el formato de Nominatim `[S, N, W, E]` al formato Overpass `"S,W,N,E"`), zoom (estimado con `Math.min(14, Math.max(9, Math.round(Math.log2(360/maxSpan))))` donde `maxSpan = max(latSpan, lonSpan)`).
- Campos editables: Latitud, Longitud, Zoom, Bbox (pre-rellenados, sobrescribibles).
- URL de áreas censales + campo identificador (con tooltip ℹ explicando su función).
- Radio de accesibilidad en metros.

**Sección 2 — Servicios:**
- Lista dinámica pre-cargada con los 7 servicios de Valencia (inyectados como constante `DEFAULTS` en JavaScript).
- Cada tarjeta de servicio contiene:
  - Input de emoji (1–2 caracteres).
  - Input de etiqueta (`label`), que auto-genera el `id` (normalización: lowercase, elimina acentos, sustituye espacios por guion bajo).
  - Selector de tipo: `url` / `overpass` (muestra/oculta el campo correspondiente).
  - Textarea de URL o query Overpass.
  - Campo `name_field` con tooltip ℹ.
  - Sección desplegable `<details>` de filtro opcional (campo + subcadena) con tooltip ℹ.
  - Botón eliminar (✕).
- Botón "＋ Añadir servicio" que clona un `<template>` HTML5.

**Sección 3 — Descargar:**
- Nota informativa explicando el flujo (descargar → colocar en proyecto → ejecutar Python).
- Botón "Ver YAML": genera y muestra el YAML en un `<pre>` con tema oscuro.
- Botón "⬇ Descargar config.yaml": genera un `Blob`, crea una URL temporal con `URL.createObjectURL()` y dispara la descarga.

### 7.4 Tooltips de información (ℹ)

Implementados en CSS puro con `position:relative` + pseudo-elemento `::after` con `content: attr(data-tip)` + transición de opacidad. Tres tooltips:

1. **Campo identificador de área**: explica que identifica cada sección censal en el tooltip del mapa (p. ej. código INE).
2. **Campo de nombre** (en cada servicio): explica que es el nombre del servicio más próximo mostrado en el tooltip al pasar el cursor.
3. **Filtro de campo**: explica que permite usar un GeoJSON con varios tipos de elementos (p. ej. todos los centros educativos) filtrando solo los relevantes.

### 7.5 Enlace desde el mapa principal

`main.py` añade al HTML generado un enlace fijo en la esquina superior derecha:

```html
<a href="configurar.html" style="position:fixed;top:12px;right:12px;...">
  ⚙ Generador de configuración
</a>
```

Esto garantiza que el enlace persiste en cada regeneración del mapa.

---

## 8. Mapa principal: `docs/index.html`

Fichero generado por `main.py`. No se edita manualmente.

**Capas Folium/Leaflet:**

1. **GeoJson de secciones censales**: coloreado por score (0–N). Tooltip al hover con todos los campos de accesibilidad.
2. **FeatureGroup de emojis**: marcadores DivIcon sobre el centroide UTM proyectado a WGS84. Solo visible desde `emoji_min_zoom`.
3. **Leyenda fija**: escala de colores (uno por score) + lista de emojis por servicio.
4. **Enlace fijo** a `configurar.html`.

**Paleta de colores**: gradiente continuo del colormap `RdYlGn` de matplotlib, con 0 = rojo puro y N = verde puro. El color se precomputa para cada valor posible de score (dict `color_cache`) para evitar recalcularlo en cada feature durante el renderizado.

**Emojis de servicios faltantes**: para cada sección censal, se recorren los servicios con emoji y se muestra el emoji de los que tengan `{id}_ok == False`. El marcador se posiciona en el centroide UTM convertido a WGS84 (no en el centroide del polígono WGS84, que sería menos preciso).

---

## 9. Publicación: GitHub Pages

La carpeta `docs/` se sirve directamente desde GitHub Pages (rama `main`). El mapa (`index.html`), el mapa GTFS (`mapa_gtfs.html`) y el formulario (`configurar.html`) son accesibles públicamente.

La generación de los mapas es **manual**: no hay CI/CD. El usuario ejecuta `main.py` y `map_gtfs.py` localmente y hace push del resultado.

---

## 10. Limitaciones actuales y líneas de trabajo futuro

### Limitaciones

1. **Modo transit no integrado en `main.py`**: el motor GTFS (`gtfs.py`) está implementado y validado mediante `map_gtfs.py`, pero el bucle de análisis de `main.py` aún no lo usa. La integración requiere precomputar `reachable_from()` por centroide y sustituir la lógica de `_nearest`.

2. **Distancia euclídea en modo distance**: no considera la red viaria real (network distance). La distancia real peatonal puede ser significativamente mayor que la línea recta, especialmente en zonas con barreras físicas (vías, ríos, autovías).

3. **Isócrona por casco convexo**: `reachable_hull()` calcula el casco convexo de las paradas alcanzables, que sobreestima el área real accesible (un convex hull puede incluir zonas sin cobertura real).

4. **Modelo de espera simplificado**: el headway se estima asumiendo un período de servicio de 16 h uniformes. No distingue entre horas punta y valle, ni entre días laborables y festivos.

5. **Sin ponderación por población**: todas las secciones censales tienen el mismo peso en los cálculos agregados, independientemente de su número de habitantes.

6. **URL de EMT dependiente de fecha**: el nombre del fichero ZIP incluye la fecha de publicación (`google_transit2026-05-31.zip`), por lo que la URL en `config.yaml` debe actualizarse manualmente cada vez que la EMT actualiza el feed.

7. **Sin tests automatizados**.

### Líneas de trabajo futuro

- Integrar el modo transit en `main.py` (sustituir `_nearest` por `TransitGraph.service_min_time`).
- Implementar isócrona alfa-shape (concave hull) en lugar de convex hull para una representación más precisa.
- Añadir análisis de equidad: ponderar el score de accesibilidad por densidad de población o renta media por sección.
- Soporte para modo bicicleta (radio de influencia fijo o red ciclista GeoJSON).
- Actualización automática del feed EMT (scraping del portal VLCI para obtener siempre la URL del ZIP más reciente).
- CI/CD para regenerar los mapas al hacer push a `main`.

---

## 11. Cómo reproducir el entorno

```bash
# 1. Clonar el repositorio
git clone https://github.com/olau-am/quinzemin
cd quinzemin

# 2. Crear entorno virtual e instalar dependencias
python -m venv .venv
.venv/Scripts/activate     # Windows
# source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
pip install requests urllib3  # (no declarados en requirements.txt aún)

# 3. Descargar datos
python src/download_data.py

# 4. Generar mapa de accesibilidad (modo distance)
python src/main.py

# 5. (Opcional) Generar mapa de isócronas GTFS
#    Requiere que los ZIPs GTFS estén descargados
python src/map_gtfs.py
```

El formulario `docs/configurar.html` se puede abrir directamente en un navegador (fichero local o GitHub Pages) sin ejecutar ningún script Python.
