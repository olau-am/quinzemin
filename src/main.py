import os
import folium
import webbrowser
import geopandas as gpd


# (ruta, campo de nombre, función de filtro opcional)
SERVICES = {
    "salud":         ("data/ca_centros_salud.geojson",  "cen_desclar", None),
    "primaria":      ("data/centros_educativos.geojson", "dlibre",
                      lambda df: df[df["dgenerica"].str.contains("PRIMÀR", case=False, na=False)]),
    "secundaria":    ("data/centros_educativos.geojson", "dlibre",
                      lambda df: df[df["dgenerica"].str.contains("SECUNDÀR", case=False, na=False)]),
    "transporte":    ("data/metro.geojson",              "nombre",      None),
    "supermercados": ("data/supermercados.geojson",      "name",        None),
}

# Gradiente rojo → naranja → amarillo → amarillo-verde → verde claro → verde (0 a 5 servicios)
COLORS = ["#d73027", "#fc8d59", "#fee08b", "#d9ef8b", "#a6d96a", "#1a9641"]

LABELS = {
    "salud":         "Salud",
    "primaria":      "Ed. Primaria",
    "secundaria":    "Ed. Secundaria",
    "transporte":    "Transporte",
    "supermercados": "Supermercado",
}


def nearest(centroid, gdf, name_col):
    """Devuelve (distancia_m, nombre) del elemento más cercano al centroide."""
    distances = gdf.geometry.distance(centroid)
    idx = distances.idxmin()
    dist = round(distances[idx])
    name = gdf.at[idx, name_col] if name_col in gdf.columns else "—"
    return dist, str(name) if name else "—"


def main():
    valencia_lat = 39.4699
    valencia_lng = -0.3763

    mapa = folium.Map(location=[valencia_lat, valencia_lng], zoom_start=12)

    secciones_path = "data/secciones_censales.json"
    if not os.path.exists(secciones_path):
        print("Archivo no encontrado: secciones_censales.json")
        return

    secciones = gpd.read_file(secciones_path).to_crs(epsg=25830)
    centroids = secciones.geometry.centroid
    secciones["score"] = 0

    n_services = len(SERVICES)
    tooltip_fields  = ["coddistsecc", "score"]
    tooltip_aliases = ["Sección censal:", f"Servicios accesibles (0–{n_services}):"]

    for svc_name, (path, name_col, filter_fn) in SERVICES.items():
        dist_col   = f"dist_{svc_name}_m"
        nombre_col = f"nombre_{svc_name}"
        ok_col     = f"{svc_name}_1km"
        label      = LABELS[svc_name]

        if os.path.exists(path):
            gdf = gpd.read_file(path).to_crs(epsg=25830)
            if filter_fn is not None:
                gdf = filter_fn(gdf).reset_index(drop=True)
            results = centroids.apply(lambda c, g=gdf, nc=name_col: nearest(c, g, nc))
            secciones[dist_col]   = results.apply(lambda r: r[0])
            secciones[nombre_col] = results.apply(lambda r: r[1])
            secciones[ok_col]     = secciones[dist_col] <= 1000
            secciones["score"]   += secciones[ok_col].astype(int)
            n = int(secciones[ok_col].sum())
            print(f"{label}: {n}/{len(secciones)} secciones con acceso <1km ({len(gdf)} centros)")
        else:
            secciones[dist_col]   = None
            secciones[nombre_col] = "—"
            secciones[ok_col]     = False
            print(f"Archivo no encontrado: {path}")

        tooltip_fields  += [ok_col, nombre_col, dist_col]
        tooltip_aliases += [
            f"{label} <1km:",
            f"Más cercano:",
            f"Distancia (m):",
        ]

    secciones = secciones.to_crs(epsg=4326)

    folium.GeoJson(
        secciones,
        style_function=lambda f: {
            "fillColor": COLORS[min(int(f["properties"]["score"] or 0), len(COLORS) - 1)],
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

    output_dir = "docs"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "index.html")
    mapa.save(output_file)
    print(f"Mapa guardado en {output_file}")
    webbrowser.open(output_file)


if __name__ == "__main__":
    main()
