import os
import json
import urllib3
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


def _download_url(url: str, destination: str, verify: bool = True) -> None:
    if not verify:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    response = requests.get(url, headers=_HEADERS, stream=True, timeout=60, verify=verify)
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


def _fetch_source_features(src: dict, bbox: str) -> list:
    """Descarga una fuente individual y devuelve su lista de features GeoJSON."""
    src_type = src.get("type", "url")
    if src_type == "overpass":
        query = src["overpass_query"].replace("{bbox}", bbox)
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
                return _osm_to_geojson(response.json())["features"]
            except Exception as e:
                print(f"  Mirror {mirror} falló: {e}")
                last_error = e
        raise RuntimeError(f"Todos los mirrors fallaron. Último error: {last_error}")
    else:
        verify = src.get("verify_ssl", True)
        if not verify:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        response = requests.get(src["url"], headers=_HEADERS, stream=True, timeout=60, verify=verify)
        response.raise_for_status()
        return response.json().get("features", [])


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
            if "sources" in svc:
                # Múltiples fuentes: descargar cada una y combinar features
                service_name_field = svc.get("name_field")
                all_features = []
                source_labels = []
                for src in svc["sources"]:
                    src_label = src.get("label", src.get("type", "?"))
                    try:
                        features = _fetch_source_features(src, bbox)
                        # Normalizar nombre: si la fuente usa un campo distinto al del servicio,
                        # copiarlo para que main.py encuentre siempre el mismo campo.
                        src_name_field = src.get("name_field")
                        if src_name_field and service_name_field and src_name_field != service_name_field:
                            for f in features:
                                props = f.get("properties") or {}
                                if src_name_field in props and service_name_field not in props:
                                    props[service_name_field] = props[src_name_field]
                        all_features.extend(features)
                        source_labels.append(f"{src_label} ({len(features)})")
                    except Exception as e:
                        print(f"  ✗ Fuente '{src_label}': {e}")
                geojson = {"type": "FeatureCollection", "features": all_features}
                with open(dest, "w", encoding="utf-8") as f:
                    json.dump(geojson, f, ensure_ascii=False)
                print(f"✓ {svc['label']}: {dest} ({len(all_features)} elementos — {', '.join(source_labels)})")

            elif svc_type == "overpass":
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

    # GTFS — se descarga siempre que haya fuentes configuradas,
    # independientemente de analysis.mode (map_gtfs.py funciona en cualquier modo)
    for src in cfg.get("analysis", {}).get("gtfs_sources", []):
        src_id  = src.get("id", "gtfs")
        src_url = src.get("url", "").strip()
        label   = src.get("label", src_id)
        verify  = src.get("verify_ssl", True)   # false para sitios con cert FNMT/GVA
        dest    = os.path.join(output_dir, f"gtfs_{src_id}.zip")
        if not src_url:
            print(f"⚠ Sin URL para GTFS {label} — omitida")
            continue
        try:
            _download_url(src_url, dest, verify=verify)
            print(f"✓ GTFS {label}: {dest}")
        except Exception as e:
            print(f"✗ Error descargando GTFS {label}: {e}")


if __name__ == "__main__":
    descargar_todos_los_archivos()
