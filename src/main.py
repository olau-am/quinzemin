import os
import webbrowser

import folium
from branca.element import Element
import geopandas as gpd
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt

import config


def _legend_html(color_cache: dict, n_services: int, threshold_label: str, services: list) -> str:
    score_rows = ""
    for score in range(n_services + 1):
        color = color_cache[score]
        if score == 0:
            label = "0 — ninguno"
        elif score == n_services:
            label = f"{score} — todos"
        else:
            label = str(score)
        score_rows += (
            f'<div style="display:flex;align-items:center;margin:3px 0">'
            f'<div style="width:18px;height:18px;background:{color};border:1px solid #666;'
            f'margin-right:7px;flex-shrink:0;border-radius:2px"></div>'
            f'<span>{label}</span></div>'
        )

    emoji_rows = ""
    for svc in services:
        emoji = svc.get("emoji")
        if emoji:
            emoji_rows += (
                f'<div style="display:flex;align-items:center;margin:3px 0">'
                f'<span style="font-size:16px;width:22px;text-align:center;margin-right:5px">{emoji}</span>'
                f'<span>{svc["label"]}</span></div>'
            )

    emoji_section = (
        f'<hr style="border:none;border-top:1px solid #ddd;margin:8px 0"/>'
        f'<b style="font-size:11px;color:#666;text-transform:uppercase;letter-spacing:.5px">Servicios</b>'
        f'<div style="margin-top:4px">{emoji_rows}</div>'
    ) if emoji_rows else ""

    return (
        '<div style="position:fixed;bottom:30px;right:10px;z-index:1000;background:white;'
        'padding:10px 14px;border-radius:6px;border:1px solid #aaa;font-size:13px;'
        'font-family:sans-serif;box-shadow:2px 2px 6px rgba(0,0,0,.3);line-height:1.4">'
        f'<b>Servicios {threshold_label}</b><br/><br/>'
        f'{score_rows}'
        f'{emoji_section}'
        '</div>'
    )


def _score_color(score: int, max_score: int) -> str:
    """Mapea un score 0..max_score a un color hex del gradiente RdYlGn."""
    if max_score == 0:
        return "#808080"
    cmap = plt.get_cmap("RdYlGn")
    return mcolors.to_hex(cmap(score / max_score))


def _nearest(centroid, gdf, name_col: str) -> tuple[int, str]:
    """Devuelve (distancia_m, nombre) del elemento más cercano al centroide."""
    distances = gdf.geometry.distance(centroid)
    idx = distances.idxmin()
    dist = round(float(distances[idx]))
    name = gdf.at[idx, name_col] if name_col in gdf.columns else ""
    return dist, str(name) if name else "—"


def main() -> None:
    cfg      = config.load()
    city     = cfg["city"]
    services = cfg["services"]
    analysis   = cfg.get("analysis", {})
    dist_m     = analysis.get("distance_m", 1000)
    mode       = analysis.get("mode", "distance")
    transit    = mode == "transit"
    time_min   = analysis.get("time_minutes", 15)
    budget_s   = time_min * 60
    walk_mps   = analysis.get("walking_speed_mpm", 80) / 60
    max_walk_m = analysis.get("max_walk_to_stop_m", 500)

    lat, lon = city["center"]
    mapa = folium.Map(location=[lat, lon], zoom_start=city["zoom"], attr=config.build_attr(cfg))

    # --- Cargar áreas de análisis ---
    areas_path = "data/areas.geojson"
    if not os.path.exists(areas_path):
        print(f"Archivo no encontrado: {areas_path}. Ejecuta download_data.py primero.")
        return

    areas = gpd.read_file(areas_path)
    # CRS proyectado óptimo para la ciudad (metros reales, sin hardcodear EPSG)
    utm = areas.estimate_utm_crs()
    areas = areas.to_crs(utm)
    centroids = areas.geometry.centroid
    areas["score"] = 0

    # --- Cargar grafo GTFS si mode=transit ---
    graph     = None
    reachable = None
    if transit:
        from gtfs import TransitGraph
        sources = [
            {"id": s["id"], "label": s.get("label", s["id"]),
             "path": f"data/gtfs_{s['id']}.zip"}
            for s in analysis.get("gtfs_sources", [])
            if os.path.exists(f"data/gtfs_{s['id']}.zip")
        ]
        if sources:
            graph = TransitGraph.load(sources, utm)
            print(f"Calculando alcance por transporte público ({len(areas)} centroides)...")
            reachable = {idx: graph.reachable_from(c, budget_s, walk_mps, max_walk_m)
                         for idx, c in centroids.items()}
            print("  Listo.")
        else:
            print("⚠ No hay datos GTFS disponibles — usando modo distancia")
            transit = False

    id_field        = city["areas"]["id_field"]
    n_services      = len(services)
    tooltip_fields  = [id_field, "score"]
    tooltip_aliases = [
        "Área:",
        f"Servicios accesibles (0–{n_services}):",
    ]

    # --- Procesar cada servicio ---
    for svc in services:
        svc_id     = svc["id"]
        label      = svc["label"]
        name_col   = svc.get("name_field", "name")
        threshold  = svc.get("distance_m", dist_m)   # distancia global o por servicio
        svc_filter = svc.get("filter")

        dist_col   = f"dist_{svc_id}_m"
        nombre_col = f"nombre_{svc_id}"
        ok_col     = f"{svc_id}_ok"
        path       = f"data/{svc_id}.geojson"

        if os.path.exists(path):
            gdf = gpd.read_file(path).to_crs(utm)

            if svc_filter:
                mask = gdf[svc_filter["field"]].str.contains(
                    svc_filter["contains"], case=False, na=False
                )
                gdf = gdf[mask].reset_index(drop=True)

            if transit:
                dists, names = [], []
                for idx in areas.index:
                    t, name = graph.service_min_time(
                        reachable[idx], gdf, name_col, walk_mps, budget_s, max_walk_m
                    )
                    dists.append(round(t / 60) if t is not None else 9999)
                    names.append(name)
                areas[dist_col]  = dists
                areas[nombre_col]= names
                areas[ok_col]    = areas[dist_col] <= time_min
                n = int(areas[ok_col].sum())
                print(f"{label}: {n}/{len(areas)} áreas con acceso <{time_min}min")
            else:
                results          = centroids.apply(lambda c, g=gdf, nc=name_col: _nearest(c, g, nc))
                areas[dist_col]  = results.apply(lambda r: r[0])
                areas[nombre_col]= results.apply(lambda r: r[1])
                areas[ok_col]    = areas[dist_col] <= threshold
                n = int(areas[ok_col].sum())
                print(f"{label}: {n}/{len(areas)} áreas con acceso <{threshold}m ({len(gdf)} elementos)")
            areas["score"] += areas[ok_col].astype(int)
        else:
            areas[dist_col]  = None
            areas[nombre_col]= "—"
            areas[ok_col]    = False
            print(f"Archivo no encontrado: {path}")

        tooltip_fields += [ok_col, nombre_col, dist_col]
        if transit:
            tooltip_aliases += [
                f"{label} <{time_min}min:",
                "Más cercano:",
                "Tiempo (min):",
            ]
        else:
            tooltip_aliases += [
                f"{label} <{threshold}m:",
                "Más cercano:",
                "Distancia (m):",
            ]

    # --- Renderizar mapa ---
    areas_wgs84       = areas.to_crs(epsg=4326)
    centroids_wgs84   = centroids.to_crs(epsg=4326)

    # Precomputar colores para los scores distintos (evita recalcular en cada feature)
    color_cache = {s: _score_color(s, n_services) for s in range(n_services + 1)}

    folium.GeoJson(
        areas_wgs84,
        style_function=lambda f, cache=color_cache: {
            "fillColor": cache[min(int(f["properties"]["score"] or 0), n_services)],
            "color": "#555",
            "weight": 0.5,
            "fillOpacity": 0.65,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=tooltip_fields,
            aliases=tooltip_aliases,
            localize=True,
        ),
    ).add_to(mapa)

    # --- Emojis de servicios faltantes (visibles desde emoji_min_zoom) ---
    emoji_min_zoom = cfg.get("map", {}).get("emoji_min_zoom", 14)
    svcs_with_emoji = [s for s in services if s.get("emoji")]

    if svcs_with_emoji:
        # show=True: la capa se añade al mapa; el JS la oculta si zoom < min_zoom
        emoji_fg = folium.FeatureGroup(name="Servicios faltantes", show=True)
        ok_cols  = {s["id"]: f"{s['id']}_ok" for s in svcs_with_emoji}
        n_emoji  = 0

        for idx, row in areas_wgs84.iterrows():
            missing = []
            for s in svcs_with_emoji:
                col = ok_cols[s["id"]]
                if col in areas_wgs84.columns and not bool(row[col]):
                    missing.append(s["emoji"])
            if not missing:
                continue

            c    = centroids_wgs84[idx]
            n    = len(missing)
            text = "".join(missing)
            folium.Marker(
                location=[c.y, c.x],
                icon=folium.DivIcon(
                    html=(
                        f'<div style="font-size:18px;line-height:1;white-space:nowrap;'
                        f'filter:drop-shadow(0 0 3px rgba(255,255,255,0.9))">{text}</div>'
                    ),
                    icon_size=(n * 22, 22),
                    icon_anchor=(n * 11, 11),
                    class_name="",   # elimina el wrapper extra de Folium
                ),
            ).add_to(emoji_fg)
            n_emoji += 1

        emoji_fg.add_to(mapa)
        print(f"Emoji markers: {n_emoji} áreas con servicios faltantes")

        map_var = mapa.get_name()
        fg_var  = emoji_fg.get_name()
        # Llamada directa (no whenReady): el script se ejecuta después de que
        # el mapa ya está inicializado, por lo que getZoom() es válido de inmediato.
        mapa.get_root().html.add_child(Element(
            "<script>"
            "(function(){"
            f"var _m={map_var},_fg={fg_var},_mz={emoji_min_zoom};"
            "function _upd(){"
            "if(_m.getZoom()>=_mz){if(!_m.hasLayer(_fg))_m.addLayer(_fg);}"
            "else{if(_m.hasLayer(_fg))_m.removeLayer(_fg);}"
            "}"
            "_m.on('zoomend',_upd);"
            "_upd();"
            "})();"
            "</script>"
        ))

    output_dir  = "docs"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "index.html")
    threshold_label = (
        f"en &lt;{time_min} min · transporte público"
        if transit else
        f"a &lt;{dist_m} m"
    )
    mapa.get_root().html.add_child(Element(_legend_html(color_cache, n_services, threshold_label, services)))
    mapa.get_root().html.add_child(Element(
        '<a href="configurar.html" style="position:fixed;top:12px;right:12px;z-index:1000;'
        'background:white;border:1px solid #aaa;border-radius:6px;padding:7px 12px;'
        'font-size:12px;font-family:sans-serif;text-decoration:none;color:#1e40af;'
        'box-shadow:2px 2px 6px rgba(0,0,0,.2);font-weight:600">'
        '⚙ Generador de configuración</a>'
    ))

    mapa.save(output_file)
    print(f"\nMapa guardado en {output_file}")
    webbrowser.open(output_file)


if __name__ == "__main__":
    main()
