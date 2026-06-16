import os
import json
import requests

# Fuentes de datos abiertos (datos.gob.es y portales municipales/autonómicos)
data_sources = {
    "secciones_censales.json": "https://geoportal.valencia.es/server/rest/services/OPENDATA/UrbanismoEInfraestructuras/MapServer/210/query?where=1=1&outFields=*&f=geojson",
    "traffic_valencia.json": "https://geoportal.valencia.es/server/rest/services/OPENDATA/Trafico/MapServer/188/query?where=1=1&outFields=*&f=geojson",
    "ca_centros_salud.geojson": "https://terramapas.icv.gva.es/15_SistemaValencianoSalud?request=GetFeature&service=WFS&version=2.0.0&typename=CentrosSanitarios.CentrosSalud&outputformat=geojson",
    "ca_hospitales.geojson": "https://terramapas.icv.gva.es/15_SistemaValencianoSalud?request=GetFeature&service=WFS&version=2.0.0&typename=CentrosSanitarios.Hospitales&outputformat=geojson",
    "centros_educativos.geojson": "https://opendata.vlci.valencia.es/dataset/11436f0c-082b-4e5b-9659-005f5b528bde/resource/938e34b7-bb7d-4b0c-8176-3602d47ebd6a/download/centros-educativos-en-valencia.geojson",
    "metro.geojson": "https://geoportal.valencia.es/server/rest/services/OPENDATA/Trafico/MapServer/221/query?where=1=1&outFields=*&f=geojson",
    "valenbisi-disponibilitat.geojson": "https://geoportal.valencia.es/server/rest/services/OPENDATA/Trafico/MapServer/228/query?where=1=1&outFields=*&f=geojson",
    # tweets_valencia.geojson eliminado: los datos de Twitter/X no son datos abiertos gubernamentales
}

# Bounding box de la ciudad de Valencia (S, W, N, E)
_VALENCIA_BBOX = "39.38,-0.45,39.55,-0.29"

# Overpass API: supermercados en Valencia (OpenStreetMap, licencia ODbL)
_OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
_OVERPASS_QUERY = (
    f'[out:json][timeout:60];'
    f'(node["shop"="supermarket"]({_VALENCIA_BBOX});'
    f'way["shop"="supermarket"]({_VALENCIA_BBOX}););'
    f'out center;'
)
_HEADERS = {"User-Agent": "quinzemin/1.0 (ciudad-15-minutos)"}


def _osm_to_geojson(osm_data):
    """Convierte la respuesta JSON de Overpass a GeoJSON FeatureCollection."""
    features = []
    for el in osm_data.get("elements", []):
        if el["type"] == "node":
            lon, lat = el["lon"], el["lat"]
        elif el["type"] == "way" and "center" in el:
            lon, lat = el["center"]["lon"], el["center"]["lat"]
        else:
            continue
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {**el.get("tags", {}), "osm_id": el["id"]},
        })
    return {"type": "FeatureCollection", "features": features}


def descargar_archivo(url, destination):
    response = requests.get(url, stream=True, timeout=60)
    response.raise_for_status()
    with open(destination, "wb") as f:
        f.write(response.content)
    print(f"✓ Descargado: {destination}")


def descargar_supermercados(destination):
    last_error = None
    for mirror in _OVERPASS_MIRRORS:
        try:
            response = requests.get(
                mirror,
                params={"data": _OVERPASS_QUERY},
                headers=_HEADERS,
                timeout=90,
            )
            response.raise_for_status()
            geojson = _osm_to_geojson(response.json())
            with open(destination, "w", encoding="utf-8") as f:
                json.dump(geojson, f, ensure_ascii=False)
            print(f"✓ Descargado: {destination} ({len(geojson['features'])} supermercados)")
            return
        except Exception as e:
            print(f"  Mirror {mirror} falló: {e}")
            last_error = e
    raise RuntimeError(f"Todos los mirrors fallaron. Último error: {last_error}")


def descargar_todos_los_archivos(output_dir="data"):
    os.makedirs(output_dir, exist_ok=True)

    for file_name, url in data_sources.items():
        destination = os.path.join(output_dir, file_name)
        try:
            descargar_archivo(url, destination)
        except Exception as e:
            print(f"✗ Error descargando {file_name}: {e}")

    try:
        descargar_supermercados(os.path.join(output_dir, "supermercados.geojson"))
    except Exception as e:
        print(f"✗ Error descargando supermercados: {e}")


if __name__ == "__main__":
    descargar_todos_los_archivos()
