import os
import folium
import webbrowser
import geopandas as gpd


def main():
    valencia_lat = 39.4699
    valencia_lng = -0.3763

    mapa = folium.Map(location=[valencia_lat, valencia_lng], zoom_start=12)

    secciones_path = "data/secciones_censales.json"
    centros_path = "data/ca_centros_salud.geojson"

    if os.path.exists(secciones_path) and os.path.exists(centros_path):
        secciones = gpd.read_file(secciones_path)
        centros = gpd.read_file(centros_path)

        # Proyectar a EPSG:25830 (UTM, metros) para calcular distancias reales
        secciones = secciones.to_crs(epsg=25830)
        centros = centros.to_crs(epsg=25830)

        centroids = secciones.geometry.centroid

        # Para cada sección, distancia mínima desde su centroide al centro de salud más cercano
        secciones["dist_min_m"] = centroids.apply(
            lambda c: centros.geometry.distance(c).min()
        )
        secciones["centro_1km"] = secciones["dist_min_m"] <= 1000

        # Volver a WGS84 para folium
        secciones = secciones.to_crs(epsg=4326)

        folium.GeoJson(
            secciones,
            style_function=lambda f: {
                "fillColor": "#2ecc71" if f["properties"]["centro_1km"] else "#e74c3c",
                "color": "#555",
                "weight": 0.5,
                "fillOpacity": 0.55,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["centro_1km", "dist_min_m"],
                aliases=["Centro de salud a <1km:", "Distancia al más cercano (m):"],
                localize=True,
            ),
        ).add_to(mapa)

        con = int(secciones["centro_1km"].sum())
        sin = len(secciones) - con
        print(f"Secciones con centro a <1km: {con} | sin: {sin}")

    output_dir = "docs"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "index.html")

    mapa.save(output_file)
    print(f"Mapa guardado en {output_file}")
    webbrowser.open(output_file)


if __name__ == "__main__":
    main()
