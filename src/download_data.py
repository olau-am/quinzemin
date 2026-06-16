import os
import requests

# Fuentes de datos abiertos (datos.gob.es y portales municipales/autonómicos)
data_sources = {
    "secciones_censales.json": "https://geoportal.valencia.es/apps/OpenData/UrbanismoEInfraestructuras/SecCensales.json",
    "traffic_valencia.json": "https://geoportal.valencia.es/server/rest/services/OPENDATA/Trafico/MapServer/188/query?where=1=1&outFields=*&f=geojson",
    "ca_centros_salud.geojson": "https://terramapas.icv.gva.es/15_SistemaValencianoSalud?request=GetFeature&service=WFS&version=2.0.0&typename=CentrosSanitarios.CentrosSalud&outputformat=geojson",
    "ca_hospitales.geojson": "https://terramapas.icv.gva.es/15_SistemaValencianoSalud?request=GetFeature&service=WFS&version=2.0.0&typename=CentrosSanitarios.Hospitales&outputformat=geojson",
    "centros_educativos.geojson": "https://opendata.vlci.valencia.es/dataset/11436f0c-082b-4e5b-9659-005f5b528bde/resource/938e34b7-bb7d-4b0c-8176-3602d47ebd6a/download/centros-educativos-en-valencia.geojson",
    "metro.geojson": "https://geoportal.valencia.es/server/rest/services/OPENDATA/Trafico/MapServer/221/query?where=1=1&outFields=*&f=geojson",
    "valenbisi-disponibilitat.geojson": "https://geoportal.valencia.es/server/rest/services/OPENDATA/Trafico/MapServer/228/query?where=1=1&outFields=*&f=geojson",
    # tweets_valencia.geojson eliminado: los datos de Twitter/X no son datos abiertos gubernamentales
}


def descargar_archivo(url, destination):
    response = requests.get(url, stream=True, timeout=60)
    response.raise_for_status()
    with open(destination, "wb") as f:
        f.write(response.content)
    print(f"✓ Descargado: {destination}")


def descargar_todos_los_archivos(output_dir="data"):
    os.makedirs(output_dir, exist_ok=True)

    for file_name, url in data_sources.items():
        destination = os.path.join(output_dir, file_name)
        try:
            descargar_archivo(url, destination)
        except Exception as e:
            print(f"✗ Error descargando {file_name}: {e}")


if __name__ == "__main__":
    descargar_todos_los_archivos()
