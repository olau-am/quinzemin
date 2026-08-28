"""
Visualización de isócronas de transporte público por sección censal.
Genera docs/mapa_gtfs.html mostrando:
  - Contorno de secciones censales (fondo)
  - Isócronas: casco convexo de las paradas alcanzables en N minutos (azul semitransparente)
  - Paradas GTFS coloreadas por nº de secciones que las alcanzan (capa opcional)

Uso:
  python src/map_gtfs.py

Requisitos:
  - data/gtfs_{id}.zip  por cada fuente en analysis.gtfs_sources de config.yaml
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

sys.path.insert(0, os.path.dirname(__file__))
import config
from gtfs import TransitGraph


def _hex_color(cmap, ratio: float) -> str:
    return mcolors.to_hex(cmap(max(0.0, min(1.0, ratio))))


def main() -> None:
    cfg      = config.load()
    city     = cfg["city"]
    analysis = cfg.get("analysis", {})

    budget_s   = analysis.get("time_minutes", 15) * 60
    walk_mps   = analysis.get("walking_speed_mpm", 80) / 60
    max_walk_m = analysis.get("max_walk_to_stop_m", 500)

    areas_path = "data/areas.geojson"
    if not os.path.exists(areas_path):
        print(f"Archivo no encontrado: {areas_path}")
        print("  → Ejecuta: python src/download_data.py")
        return

    # Construir lista de fuentes GTFS disponibles
    gtfs_cfg = analysis.get("gtfs_sources", [])
    sources  = []
    for src in gtfs_cfg:
        path = os.path.join("data", f"gtfs_{src['id']}.zip")
        if os.path.exists(path):
            sources.append({"id": src["id"], "label": src.get("label", src["id"]), "path": path})
        else:
            print(f"⚠ No encontrado: {path}")

    if not sources:
        print("No hay datos GTFS disponibles.")
        print("  → Activa analysis.mode: transit en config.yaml")
        print("  → Ejecuta: python src/download_data.py")
        return

    print("Cargando áreas censales...")
    areas     = gpd.read_file(areas_path)
    utm       = areas.estimate_utm_crs()
    areas     = areas.to_crs(utm)
    centroids = areas.geometry.centroid

    print("Cargando grafo GTFS...")
    graph = TransitGraph.load(sources, utm)

    budget_min = budget_s // 60
    n_areas    = len(areas)
    print(f"Calculando isócronas: {n_areas} secciones × {budget_min} min "
          f"(a pie max {max_walk_m}m, {walk_mps*60:.0f}m/min)...")

    hulls         = []
    reach_count   = defaultdict(int)   # stop_id → cuántas áreas lo alcanzan

    for i, (idx, centroid) in enumerate(centroids.items()):
        if i % 100 == 0:
            print(f"  {i}/{n_areas}")
        r    = graph.reachable_from(centroid, budget_s, walk_mps, max_walk_m)
        hull = graph.reachable_hull(r, buffer_m=150)
        hulls.append(hull)
        for sid in r:
            reach_count[sid] += 1

    print(f"  {n_areas}/{n_areas} — listo")

    # GeoDataFrame de isócronas en WGS84
    iso_gdf = gpd.GeoDataFrame(
        areas[[city["areas"]["id_field"]]].copy(),
        geometry=hulls,
        crs=utm,
    ).dropna(subset=["geometry"]).to_crs(epsg=4326)

    # Paradas con score de accesibilidad
    stops_gdf             = graph.stops_geodataframe()
    stops_gdf["n_areas"]  = stops_gdf["stop_id"].map(reach_count).fillna(0).astype(int)
    max_reach             = stops_gdf["n_areas"].max() or 1
    cmap_stops            = plt.get_cmap("YlOrRd")
    stops_gdf["color"]    = stops_gdf["n_areas"].apply(
        lambda n: _hex_color(cmap_stops, n / max_reach)
    )

    # ------------------------------------------------------------------
    # Mapa Folium
    # ------------------------------------------------------------------
    lat, lon = city["center"]
    mapa = folium.Map(location=[lat, lon], zoom_start=city["zoom"])

    areas_wgs84 = areas.to_crs(epsg=4326)

    # Capa 1: isócronas (añadida primero → debajo en z-order)
    iso_lyr = folium.GeoJson(
        iso_gdf,
        style_function=lambda f: {
            "fillColor":   "#2563eb",
            "color":       "#1d4ed8",
            "weight":      0.4,
            "fillOpacity": 0.12,
        },
        name=f"Isócronas {budget_min} min (transporte público)",
        show=True,
    )
    iso_lyr.add_to(mapa)

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
        name=f"Isócronas {budget_min} min (transporte público)",
        show=True,
    )
    areas_lyr.add_to(mapa)

    # Capa 3: paradas coloreadas por cobertura (desactivada por defecto)
    stops_fg = folium.FeatureGroup(name="Paradas GTFS (cobertura)", show=False)
    for _, row in stops_gdf.iterrows():
        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=4,
            color=row["color"],
            fill=True,
            fill_color=row["color"],
            fill_opacity=0.85,
            weight=0,
            tooltip=(
                f"{row['stop_name'] or row['stop_id']} "
                f"— alcanzable desde {row['n_areas']} áreas"
            ),
        ).add_to(stops_fg)
    stops_fg.add_to(mapa)

    folium.LayerControl(collapsed=False).add_to(mapa)

    # Leyenda
    pct_covered  = 100 * iso_gdf.shape[0] / n_areas
    source_lines = "".join(
        f'<div style="color:#666">· {s["label"]}</div>' for s in sources
    )
    legend_html = (
        '<div style="position:fixed;bottom:30px;right:10px;z-index:1000;background:white;'
        'padding:10px 14px;border-radius:6px;border:1px solid #aaa;font-size:12px;'
        'font-family:sans-serif;box-shadow:2px 2px 6px rgba(0,0,0,.3)">'
        f'<b>Isócrona {budget_min} min · transporte público</b><br/>'
        f'{source_lines}'
        f'<br/>Paradas: {graph.stops_count} &nbsp;|&nbsp; '
        f'Cobertura: {iso_gdf.shape[0]}/{n_areas} ({pct_covered:.0f}%)<br/><br/>'
        '<div style="display:flex;align-items:center;gap:6px">'
        '<div style="width:18px;height:12px;background:#2563eb;opacity:0.5;border-radius:2px"></div>'
        '<span>Zona alcanzable (isócrona)</span></div>'
        '<div style="display:flex;align-items:center;gap:6px;margin-top:4px">'
        '<div style="width:18px;height:3px;background:#555"></div>'
        '<span>Sección censal</span></div>'
        '</div>'
    )
    mapa.get_root().html.add_child(Element(legend_html))

    # Hover cross-layer: área censal → resalta su isócrona en naranja
    id_field  = city["areas"]["id_field"]
    areas_var = areas_lyr.get_name()
    iso_var   = iso_lyr.get_name()
    mapa.get_root().html.add_child(Element(
        "<script>window.addEventListener('load',function(){"
        f"var _id='{id_field}',_al={areas_var},_zl={iso_var},_zb={{}};"
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
        "if(_zb[k])_zb[k].setStyle({fillColor:'#2563eb',color:'#1d4ed8',fillOpacity:0.12,weight:0.4});"
        "});"
        "});"
        "});</script>"
    ))

    output = os.path.join("docs", "mapa_gtfs.html")
    os.makedirs("docs", exist_ok=True)
    mapa.save(output)
    print(f"\nMapa guardado en {output}")
    webbrowser.open(output)


if __name__ == "__main__":
    main()
