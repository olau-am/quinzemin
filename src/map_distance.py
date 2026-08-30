"""
Visualización de zonas de accesibilidad por radio simple (distancia euclídea).
Genera docs/mapa_distancia.html mostrando:
  - Contorno de secciones censales (fondo)
  - Círculos de radio distance_m centrados en cada centroide censal (azul semitransparente)
  - Puntos de servicio coloreados por cuántas secciones los alcanzan (capa opcional)

Uso:
  python src/map_distance.py

Requisitos:
  - data/areas.geojson
"""
import os
import sys
import webbrowser
from collections import defaultdict

import folium
import geopandas as gpd
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
from branca.element import Element
from shapely.geometry import Point

sys.path.insert(0, os.path.dirname(__file__))
import config


def _hex_color(cmap, ratio: float) -> str:
    return mcolors.to_hex(cmap(max(0.0, min(1.0, ratio))))


def main() -> None:
    cfg      = config.load()
    city     = cfg["city"]
    analysis = cfg.get("analysis", {})
    services = cfg.get("services", [])

    radius_m = analysis.get("distance_m", 800)

    areas_path = "data/areas.geojson"
    if not os.path.exists(areas_path):
        print(f"Archivo no encontrado: {areas_path}")
        print("  → Ejecuta: python src/download_data.py")
        return

    print("Cargando áreas censales...")
    areas     = gpd.read_file(areas_path)
    utm       = areas.estimate_utm_crs()
    areas     = areas.to_crs(utm)
    centroids = areas.geometry.centroid

    n_areas = len(areas)
    print(f"Generando {n_areas} círculos de radio {radius_m} m...")

    # Círculo UTM → WGS84 para cada centroide
    circles_utm = centroids.buffer(radius_m)
    circles_gdf = gpd.GeoDataFrame(
        areas[[city["areas"]["id_field"]]].copy(),
        geometry=circles_utm,
        crs=utm,
    ).to_crs(epsg=4326)

    # Puntos de servicio: reach_count[svc_id][point_idx] = nº secciones que lo alcanzan
    # Un servicio es alcanzado por una sección si su punto más cercano está a ≤ radius_m
    svc_gdfs = {}
    reach_count = {}   # svc_id → {geom_idx: n_areas}

    for svc in services:
        svc_id = svc["id"]
        path   = f"data/{svc_id}.geojson"
        if not os.path.exists(path):
            continue
        gdf = gpd.read_file(path).to_crs(utm)
        svc_filter = svc.get("filter")
        if svc_filter:
            mask = gdf[svc_filter["field"]].str.contains(
                svc_filter["contains"], case=False, na=False
            )
            gdf = gdf[mask].reset_index(drop=True)
        if gdf.empty:
            continue

        # Para cada centroide, ¿qué puntos del servicio están dentro del radio?
        rc = defaultdict(int)
        for centroid in centroids:
            dists = gdf.geometry.distance(centroid)
            for i, d in enumerate(dists):
                if d <= radius_m:
                    rc[i] += 1

        svc_gdfs[svc_id]   = gdf
        reach_count[svc_id] = rc

    # ------------------------------------------------------------------
    # Mapa Folium
    # ------------------------------------------------------------------
    lat, lon = city["center"]
    mapa = folium.Map(location=[lat, lon], zoom_start=city["zoom"], attr=config.build_attr(cfg))

    areas_wgs84 = areas.to_crs(epsg=4326)

    # Capa 1: círculos de radio simple (añadida primero → debajo en z-order)
    circles_lyr = folium.GeoJson(
        circles_gdf,
        style_function=lambda f: {
            "fillColor":   "#2563eb",
            "color":       "#1d4ed8",
            "weight":      0.4,
            "fillOpacity": 0.08,
        },
        name=f"Radio {radius_m} m (distancia euclídea)",
        show=True,
    )
    circles_lyr.add_to(mapa)

    # Capa 2: contornos censales (añadida después → encima, captura eventos de ratón)
    areas_lyr = folium.GeoJson(
        areas_wgs84,
        style_function=lambda f: {
            "fillColor":   "#ffffff",
            "color":       "#888",
            "weight":      0.8,
            "fillOpacity": 0.001,
        },
        highlight_function=lambda f: {
            "color":  "#444",
            "weight": 1.8,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=[city["areas"]["id_field"]],
            aliases=["Área:"],
        ),
        name="Secciones censales",
        show=True,
    )
    areas_lyr.add_to(mapa)

    # Capa 3: puntos de servicio coloreados por cobertura (desactivada por defecto)
    if svc_gdfs:
        cmap_pts = plt.get_cmap("YlOrRd")
        svc_fg   = folium.FeatureGroup(name="Servicios (cobertura)", show=False)

        for svc in services:
            svc_id = svc["id"]
            if svc_id not in svc_gdfs:
                continue
            gdf   = svc_gdfs[svc_id].to_crs(epsg=4326)
            rc    = reach_count[svc_id]
            max_r = max(rc.values()) if rc else 1
            label = svc.get("label", svc_id)
            name_col = svc.get("name_field", "name")

            for i, row in gdf.iterrows():
                geom = row.geometry
                pt   = geom.centroid if geom.geom_type != "Point" else geom
                n    = rc.get(i, 0)
                color = _hex_color(cmap_pts, n / max(max_r, 1))
                name  = str(row[name_col]) if name_col in gdf.columns else "—"
                folium.CircleMarker(
                    location=[pt.y, pt.x],
                    radius=4,
                    color=color,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.85,
                    weight=0,
                    tooltip=f"[{label}] {name} — alcanzable desde {n} áreas",
                ).add_to(svc_fg)

        svc_fg.add_to(mapa)

    folium.LayerControl(collapsed=False).add_to(mapa)

    # Leyenda
    svc_lines = "".join(
        f'<div style="color:#666">· {s.get("emoji","·")} {s["label"]}</div>'
        for s in services
        if s["id"] in svc_gdfs
    )
    legend_html = (
        '<div style="position:fixed;bottom:30px;right:10px;z-index:1000;background:white;'
        'padding:10px 14px;border-radius:6px;border:1px solid #aaa;font-size:12px;'
        'font-family:sans-serif;box-shadow:2px 2px 6px rgba(0,0,0,.3)">'
        f'<b>Radio simple · {radius_m} m</b><br/>'
        f'{svc_lines}'
        f'<br/><div style="display:flex;align-items:center;gap:6px">'
        f'<div style="width:18px;height:12px;background:#2563eb;opacity:0.4;border-radius:50%"></div>'
        f'<span>Zona de alcance (radio {radius_m} m)</span></div>'
        f'<div style="display:flex;align-items:center;gap:6px;margin-top:4px">'
        f'<div style="width:18px;height:3px;background:#555"></div>'
        f'<span>Sección censal</span></div>'
        f'</div>'
    )
    mapa.get_root().html.add_child(Element(legend_html))

    # Hover cross-layer: área censal → resalta su círculo en naranja
    id_field    = city["areas"]["id_field"]
    areas_var   = areas_lyr.get_name()
    circles_var = circles_lyr.get_name()
    mapa.get_root().html.add_child(Element(
        "<script>window.addEventListener('load',function(){"
        f"var _id='{id_field}',_al={areas_var},_zl={circles_var},_zb={{}};"
        "_zl.eachLayer(function(l){"
        "var k=l.feature&&l.feature.properties&&l.feature.properties[_id];"
        "if(k!=null)_zb[k]=l;"
        "});"
        "_al.eachLayer(function(l){"
        "var k=l.feature&&l.feature.properties&&l.feature.properties[_id];"
        "l.on('mouseover',function(){"
        "if(_zb[k]){"
        "_zb[k].setStyle({fillColor:'#f97316',color:'#ea580c',fillOpacity:0.55,weight:1.5});"
        "_zb[k].bringToFront();"
        "_al.bringToFront();"
        "}"
        "});"
        "l.on('mouseout',function(){"
        "if(_zb[k])_zb[k].setStyle({fillColor:'#2563eb',color:'#1d4ed8',fillOpacity:0.08,weight:0.4});"
        "});"
        "});"
        "});</script>"
    ))

    output = os.path.join("docs", "mapa_distancia.html")
    os.makedirs("docs", exist_ok=True)
    mapa.save(output)
    print(f"\nMapa guardado en {output}")
    webbrowser.open(output)


if __name__ == "__main__":
    main()
