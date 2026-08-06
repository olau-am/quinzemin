import os
import json
import requests
import config

_OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
_HEADERS = {"User-Agent": "quinzemin/1.0 (ciudad-15-minutos)"}


def _osm_to_geojson(osm_data: dict) -> dict:
    features = []
    for el in osm_data.get("elements", []):
        if el["type"] == "node":
            lon, lat = el["lon"], el["lat"]
        elif el["type"] in ("way", "relation") and "center" in el:
            lon, lat = el["center"]["lon"], el["center"]["lat"]
        else:
            continue
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {**el.get("tags", {}), "osm_id": el["id"]},
        })
    return {"type": "FeatureCollection", "features": features}


def _download_url(url: str, destination: str) -> None:
    response = requests.get(url, headers=_HEADERS, stream=True, timeout=60)
    response.raise_for_status()
    with open(destination, "wb") as f:
        f.write(response.content)


def _download_overpass(query: str, destination: str) -> None:
    last_error = None
    for mirror in _OVERPASS_MIRRORS:
        try:
            response = requests.get(
                mirror,
                params={"data": f"[out:json][timeout:60];{query}"},
                headers=_HEADERS,
                timeout=90,
            )
            response.raise_for_status()
            geojson = _osm_to_geojson(response.json())
            with open(destination, "w", encoding="utf-8") as f:
                json.dump(geojson, f, ensure_ascii=False)
            return len(geojson["features"])
        except Exception as e:
            print(f"  Mirror {mirror} falló: {e}")
            last_error = e
    raise RuntimeError(f"Todos los mirrors fallaron. Último error: {last_error}")


def descargar_todos_los_archivos(output_dir: str = "data") -> None:
    cfg = config.load()
    bbox = cfg["city"]["bbox"]
    os.makedirs(output_dir, exist_ok=True)

    # Áreas de análisis
    areas_url = cfg["city"]["areas"]["url"]
    areas_dest = os.path.join(output_dir, "areas.geojson")
    try:
        _download_url(areas_url, areas_dest)
        print(f"✓ Áreas: {areas_dest}")
    except Exception as e:
        print(f"✗ Error descargando áreas: {e}")

    # Servicios
    seen_urls: dict[str, str] = {}   # url → destino ya descargado (evita duplicados)

    for svc in cfg["services"]:
        svc_id   = svc["id"]
        svc_type = svc.get("type", "url")
        dest     = os.path.join(output_dir, f"{svc_id}.geojson")

        try:
            if svc_type == "overpass":
                query = svc["overpass_query"].replace("{bbox}", bbox)
                n = _download_overpass(query, dest)
                print(f"✓ {svc['label']}: {dest} ({n} elementos)")

            else:  # type: url
                url = svc["url"]
                if url in seen_urls:
                    # mismo archivo que otro servicio → copiar en lugar de re-descargar
                    import shutil
                    shutil.copy(seen_urls[url], dest)
                    print(f"✓ {svc['label']}: {dest} (copiado de {seen_urls[url]})")
                else:
                    _download_url(url, dest)
                    seen_urls[url] = dest
                    print(f"✓ {svc['label']}: {dest}")

        except Exception as e:
            print(f"✗ Error descargando {svc['label']}: {e}")


if __name__ == "__main__":
    descargar_todos_los_archivos()
