import os
import json
import folium
import webbrowser
import geopandas as gpd


def main():
    # Coordenadas aproximadas del centro de Valencia
    valencia_lat = 39.4699
    valencia_lng = -0.3763

    mapa = folium.Map(location=[valencia_lat, valencia_lng], zoom_start=12)
    folium.Marker(
        [valencia_lat, valencia_lng],
        popup="Centro de Valencia",
        tooltip="Valencia",
        icon=folium.Icon(color="blue", icon="info-sign")
    ).add_to(mapa)

    # Cargar y mostrar secciones censales
    secciones_path = "data/secciones_censales.json"
    if os.path.exists(secciones_path):
        with open(secciones_path, "r") as f:
            secciones_data = json.load(f)

        folium.GeoJson(
            secciones_data,
            style_function=lambda _: {
                "fillColor": "#ffffcc",
                "color": "black",
                "weight": 1,
                "opacity": 0.7,
                "fillOpacity": 0.3
            }
        ).add_to(mapa)

        print(f"Secciones censales cargadas: {len(secciones_data.get('features', []))}")

    # Cargar centros de salud desde GeoJSON
    geojson_path = "data/ca_centros_salud.geojson"
    if os.path.exists(geojson_path):
        gdf = gpd.read_file(geojson_path)
        
        # Convertir coordenadas de UTM (EPSG:25830) a WGS84 (EPSG:4326)
        gdf = gdf.to_crs(epsg=4326)
        
        # Añadir marcadores de centros de salud
        for idx, row in gdf.iterrows():
            lat = row.geometry.y
            lng = row.geometry.x
            nombre = row.get("CEN_DESCLA", "Centro de Salud")
            direccion = row.get("CEN_NOMBCA", "")
            
            folium.Marker(
                [lat, lng],
                popup=f"<b>{nombre}</b><br>{direccion}",
                tooltip=nombre,
                icon=folium.Icon(color="red", icon="plus", prefix="fa")
            ).add_to(mapa)
        
        print(f"Centros de salud cargados: {len(gdf)}")



    output_dir = "docs"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "index.html")

    mapa.save(output_file)
    print(f"Mapa guardado en {output_file}")

    webbrowser.open(output_file)


if __name__ == "__main__":
    main()