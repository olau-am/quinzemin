# Quinzemin — Documentació tècnica del prototip (TFM)

> Aquest document descriu l'estat actual del repositori `quinzemin` amb l'objectiu de servir de context per a la redacció de la memòria del TFM. Descriu l'objectiu, l'arquitectura, la tecnologia i les fonts de dades utilitzades.

## 1. Objectiu del prototip

El projecte és una eina d'anàlisi i visualització que avalua fins a quin punt la ciutat de **València** compleix el model de **"ciutat dels 15 minuts"**: per a cada secció censal de la ciutat, calcula si hi ha accés a peu (≤1 km en línia recta) a una sèrie de serveis bàsics:

- Salut (centres d'atenció primària / ambulatoris)
- Educació primària
- Educació secundària
- Transport públic (metro)
- Supermercats

Per a cada secció censal es calcula una **puntuació de 0 a 5** (nombre de serveis accessibles a menys d'1 km del centroide de la secció) i es representa en un mapa interactiu coroplètic (vermell = 0 serveis accessibles, verd = 5).

## 2. Tecnologia utilitzada

| Component | Tecnologia | Ús |
|---|---|---|
| Llenguatge | Python 3.13 | Tot el pipeline |
| Anàlisi geoespacial | [`geopandas`](https://geopandas.org/) | Lectura de GeoJSON, reprojecció de coordenades, càlcul de distàncies |
| Dades tabulars | `pandas`, `numpy` | Suport a geopandas |
| Descàrrega de dades | `requests` | Descàrrega de datasets oberts (usat a `download_data.py` però **no declarat** a `requirements.txt`, veure §6) |
| Visualització | [`folium`](https://python-visualization.github.io/folium/) (embolcall Python de Leaflet.js) | Generació del mapa interactiu HTML |
| Entorn | `venv` (`.venv/`) | Aïllament de dependències |
| Publicació | Carpeta `docs/` amb `index.html` estàtic | Pensat per servir-se amb GitHub Pages (repo a `github.com/olau-am/quinzemin`); no hi ha workflow de CI, la generació és manual |

No hi ha framework web, backend ni base de dades: tot el processament és un script Python que genera un fitxer HTML estàtic autocontingut (usa CDNs externs per a Leaflet/Bootstrap/FontAwesome).

## 3. Arquitectura / pipeline

```
src/download_data.py   →   data/*.geojson, data/*.json   →   src/main.py   →   docs/index.html
   (descàrrega dades)         (dades obertes, gitignored)      (anàlisi + mapa)   (mapa publicat)
```

### 3.1 `src/download_data.py`

Descarrega els datasets oberts necessaris des de portals oficials cap a la carpeta `data/` (exclosa del control de versions, cal regenerar-la localment executant aquest script).

- Descàrrega directa per HTTP GET dels fitxers definits al diccionari `data_sources` (veure taula de fonts a §4).
- Cas especial: **supermercats**, que no provenen d'un portal de dades obertes espanyol sinó de **OpenStreetMap** via l'API **Overpass** (consulta Overpass QL filtrant `shop=supermarket` dins el bounding box de València), amb sistema de mirrors alternatius (`overpass-api.de`, `overpass.kumi.systems`, `maps.mail.ru`) per tolerància a fallades.
- Gestió d'errors bàsica: cada descàrrega és independent (un fitxer que falla no atura la resta) i s'informa per consola amb ✓/✗.

### 3.2 `src/main.py`

1. Carrega `data/secciones_censales.json` (polígons de les seccions censals de València) i reprojecta a **EPSG:25830** (ETRS89 / UTM zona 30N), sistema de coordenades mètric adequat per a càlculs de distància a la ciutat de València.
2. Calcula el **centroide** de cada secció censal.
3. Per a cada servei definit al diccionari `SERVICES` (salut, primària, secundària, transport, supermercats):
   - Carrega el GeoJSON corresponent i el reprojecta al mateix CRS mètric.
   - Aplica un filtre opcional (p. ex. per distingir centres de primària i secundària dins del mateix fitxer `centros_educativos.geojson`, filtrant pel camp `dgenerica`).
   - Calcula la distància euclidiana del centroide de cada secció al punt més proper del servei (`geometry.distance`).
   - Marca la secció com "accessible" (`<svc>_1km`) si la distància és ≤ 1000 m.
   - Suma els booleans d'accessibilitat a la columna `score` (0–5).
4. Reprojecta el resultat a **EPSG:4326** (WGS84, lat/lng) per a la visualització web.
5. Renderitza amb `folium.GeoJson` un mapa coroplètic amb:
   - Color de farciment segons `score`, amb gradient de 6 colors (vermell → verd).
   - Tooltip per secció amb la puntuació total i, per a cada servei, si és accessible, el nom del centre més proper i la distància exacta.
6. Desa el resultat a `docs/index.html` i l'obre automàticament al navegador.

**Llindar de distància:** fixat a 1 km en línia recta com a aproximació estàndard d'un desplaçament a peu d'uns 15 minuts. No es distingeix per mode de transport ni es fa servir distància per xarxa de carrers (network distance), només distància euclidiana ("en línia recta").

## 4. Fonts de dades

Totes les fonts són **dades obertes** (portals governamentals o OpenStreetMap/ODbL). Es va migrar explícitament des d'un origen previ en Google Drive cap a fonts oficials (veure `notes/sources 1.txt`, exclòs del repo).

| Fitxer | Font / portal | Llicència | Ús a `main.py` |
|---|---|---|---|
| `secciones_censales.json` | Geoportal Ajuntament de València (ArcGIS REST, capa Urbanismo e Infraestructuras) | Dades obertes municipals | **Sí** — geometria base (seccions censals) |
| `ca_centros_salud.geojson` | GVA — Sistema Valenciano de Salud (servei WFS, `terramapas.icv.gva.es`) | Dades obertes GVA | **Sí** — servei "salut" |
| `centros_educativos.geojson` | VLCi Open Data (Ajuntament de València) | Dades obertes municipals | **Sí** — filtrat per generar "primària" i "secundària" |
| `metro.geojson` | Geoportal Ajuntament de València (capa Tráfico, estacions FGV) | Dades obertes municipals | **Sí** — servei "transport" |
| `supermercados.geojson` | OpenStreetMap via Overpass API | ODbL | **Sí** — servei "supermercats" |
| `ca_hospitales.geojson` | GVA WFS (mateix servei que centres de salut) | Dades obertes GVA | **Descarregat però no utilitzat** al càlcul de puntuació actual |
| `traffic_valencia.json` | Geoportal Ajuntament de València (intensitat de trànsit per trams) | Dades obertes municipals | **Descarregat però no utilitzat** |
| `valenbisi-disponibilitat.geojson` | Geoportal Ajuntament de València (disponibilitat Valenbisi) | Dades obertes municipals | **Descarregat però no utilitzat** |
| `population_valencia.json` | (font antiga, prèvia a la migració) | — | **Fitxer llegat, no es descarrega ja des de `download_data.py` ni s'utilitza**: la coropleta per població es va eliminar del programa |
| `tweets_valencia.geojson` | Twitter/X (font antiga) | No és dada oberta governamental | **Eliminat del pipeline** (comentari explícit al codi); fitxer llegat que roman a `data/` localment però no es torna a descarregar |

Nota: la carpeta `data/` està exclosa via `.gitignore`, així que aquests fitxers **no formen part del repositori Git**; cal executar `download_data.py` per regenerar-los localment.

## 5. Estructura del repositori

```
quinzemin/
├── src/
│   ├── download_data.py   # descàrrega de dades obertes
│   └── main.py             # anàlisi geoespacial + generació del mapa
├── data/                   # dades obertes descarregades (gitignored)
├── docs/
│   └── index.html          # mapa generat (sortida, pensat per GitHub Pages)
├── notes/                  # notes de treball personals (gitignored)
├── tests/                  # buida — no hi ha tests automatitzats encara
├── requirements.txt        # numpy, pandas, geopandas, folium
└── .venv/                  # entorn virtual local
```

## 6. Estat actual i limitacions conegudes

- **Sense tests automatitzats**: la carpeta `tests/` existeix però és buida.
- **`requirements.txt` incomplet**: `download_data.py` importa `requests`, que no apareix a `requirements.txt` (només hi ha `numpy`, `pandas`, `geopandas`, `folium`).
- **Distància euclidiana, no per xarxa**: la mètrica "1 km" és línia recta des del centroide de la secció censal, no una distància real caminable pel carrerer, cosa que pot sobreestimar l'accessibilitat real.
- **Llindar fix (1 km) i únic** per a tots els serveis, sense diferenciar per tipus de servei o mode de transport.
- **Dades descarregades però no integrades**: hospitals, trànsit i Valenbisi ja es descarreguen però encara no aporten a la puntuació d'accessibilitat.
- **Sense ponderació per població**: la variable de població es va descartar deliberadament en la migració de fonts (decisió documentada a `notes/sources 1.txt`); actualment totes les seccions censals pesen igual independentment del nombre d'habitants.
- **Generació manual i estàtica**: no hi ha automatització (CI/CD) que regeneri `docs/index.html`; cal executar `main.py` a mà cada vegada que canvien les dades.
- **Sense paràmetres de configuració**: rutes, llindar de distància i seccions són constants fixades al codi (no hi ha CLI ni fitxer de configuració).

## 7. Com reproduir el prototip

```bash
pip install -r requirements.txt
python src/download_data.py   # descarrega les dades a data/
python src/main.py            # genera docs/index.html i l'obre al navegador
```
