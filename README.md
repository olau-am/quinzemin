# quinzemin

Herramienta de análisis y visualización de accesibilidad urbana basada en el modelo de la **ciudad de los 15 minutos**. Para cada sección censal calcula cuántos servicios básicos son accesibles a pie (o en transporte público) y genera un mapa interactivo coroplético.

## Uso rápido

```bash
pip install -r requirements.txt
python src/download_data.py   # descarga los datos en data/
python src/main.py            # genera docs/index.html
```

Para generar la visualización de isócronas GTFS (modo transporte público):

```bash
# 1. Activa analysis.mode: transit en config.yaml
python src/download_data.py   # descarga también los feeds GTFS
python src/map_gtfs.py        # genera docs/mapa_gtfs.html
```

El formulario de configuración para otras ciudades está disponible en `docs/configurar.html`.

---

## Fuentes de datos y atribuciones

### Áreas de análisis

| Dataset | Portal | Licencia |
|---|---|---|
| Secciones censales de València | [Geoportal Ajuntament de València](https://geoportal.valencia.es/) — OPENDATA/UrbanismoEInfraestructuras | Datos abiertos municipales |

### Servicios

| Servicio | Dataset | Fuente | Licencia |
|---|---|---|---|
| Centros de Salud | Sistema Valenciá de Salut — Centres de Salut | [ICV / GVA](https://terramapas.icv.gva.es/) (servicio WFS) | Datos abiertos GVA |
| Educación Primaria y Secundaria | Centros educativos en València | [VLCi Open Data](https://opendata.vlci.valencia.es/) — Ajuntament de València | Datos abiertos municipales |
| Transporte Público (paradas) | Paradas de transporte público | [Geoportal Ajuntament de València](https://geoportal.valencia.es/) — OPENDATA/Tráfico | Datos abiertos municipales |
| Supermercados | OpenStreetMap (`shop=supermarket`) | © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), vía [Overpass API](https://overpass-api.de/) | [ODbL 1.0](https://opendatacommons.org/licenses/odbl/) |
| Zonas Verdes | Parques y jardines de València | [Geoportal Ajuntament de València](https://geoportal.valencia.es/) — OPENDATA/MedioAmbiente | Datos abiertos municipales |
| Cultura (bibliotecas, teatros, cines, centros culturales) | OpenStreetMap (`amenity=library/theatre/cinema/arts_centre`) | © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), vía [Overpass API](https://overpass-api.de/) | [ODbL 1.0](https://opendatacommons.org/licenses/odbl/) |

### Datos GTFS (modo transporte público)

| Red | Publicador | Referencia | Licencia |
|---|---|---|---|
| Metrovalencia (metro y tranvía) | [FGV — Ferrocarrils de la Generalitat Valenciana](http://www.metrovalencia.es/) | [NAP #967](https://nap.transportes.gob.es/Files/Detail/967) | Datos abiertos GVA |
| EMT Valencia (autobuses urbanos) | [EMT — Ajuntament de València](https://www.emtvalencia.es/) | [NAP #965](https://nap.transportes.gob.es/Files/Detail/965) · [datos.gob.es](https://datos.gob.es/es/catalogo/l01462508-google-transit-lineas-paradas-horarios-de-autobuses-de-la-emt-de-valencia) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |

### Geocodificación

El formulario `configurar.html` usa [Nominatim](https://nominatim.openstreetmap.org/) para autocompletar ciudades. Los resultados proceden de datos de © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright) bajo licencia [ODbL 1.0](https://opendatacommons.org/licenses/odbl/).

---

### Nota sobre OpenStreetMap

Los datos de OpenStreetMap utilizados en este proyecto (supermercados, equipamientos culturales, geocodificación) están disponibles bajo la **Open Database License (ODbL) 1.0**. Cualquier uso o redistribución de estos datos —o de productos derivados— debe:

1. Mencionar a **© OpenStreetMap contributors** como fuente.
2. Distribuir el resultado bajo la misma licencia ODbL o una compatible (share-alike).
3. Mantener el acceso a la base de datos original o a una versión derivada.

Más información: [openstreetmap.org/copyright](https://www.openstreetmap.org/copyright)

---

## Tecnología

- **Python** — `geopandas`, `pandas`, `folium`, `requests`, `pyyaml`, `matplotlib`
- **Leaflet.js** — renderizado del mapa interactivo (vía Folium)
- **GTFS** — General Transit Feed Specification para análisis de accesibilidad por transporte público
- **Overpass API** — consultas a OpenStreetMap para supermercados y equipamientos culturales
- **Nominatim** — geocodificación en el formulario de configuración

## Documentación técnica

Ver [`DOCUMENTACIO.md`](DOCUMENTACIO.md) para la descripción detallada de la arquitectura y el pipeline (documento TFM, en catalán).
