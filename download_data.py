import requests

# IDs de archivos en Google Drive
file_ids = {
    "valenbisi-disponibilitat.geojson": "1_R3X0dpPILKoI911CqU1LjMxmN8uAfmv",
    "population_valencia.json": "1GYqiuLm5_5h1ueZJRS6djmzVs210DQob",
    "traffic_valencia.json": "1s5k0WfoBP4sXmcA8CknulKtAg92Y8Gyi",
    "tweets_valencia.geojson": "1sfbK_RysOkjQOWo4h0xy3CFpY6coVvGK",
    "ca_centros_salud.geojson": "1InHMwWx8MFMDWZrFigxmnZCc-bVHtAgj",
    "ca_hospitales.geojson": "1vCD7t2RtNCyun628GTxR_Yc2e52mmInr",
    "centros_educativos.geojson": "1y269pRUirxTVPhJo7kzM2LPZOs5V3gD4",
    "metro.geojson": "1FNSwMSADpNH0xicgvoCJMwY-M7H6j1R5"
}


def descargar_archivo_drive(file_id, destination):
    """
    Descarga un archivo de Google Drive usando su ID y lo guarda en una ubicación local.

    Parameters:
    - file_id: ID del archivo en Google Drive
    - destination: Ruta donde se guardará el archivo
    """
    url = f"https://drive.google.com/uc?id={file_id}"
    response = requests.get(url, stream=True)
    with open(destination, "wb") as f:
        f.write(response.content)
    print(f"✓ Descargado: {destination}")


def descargar_todos_los_archivos(output_dir="data"):
    """
    Descarga todos los archivos de Google Drive al directorio especificado.

    Parameters:
    - output_dir: Directorio donde se guardarán los archivos (default: 'data')
    """
    import os
    os.makedirs(output_dir, exist_ok=True)

    for file_name, file_id in file_ids.items():
        destination = os.path.join(output_dir, file_name)
        try:
            descargar_archivo_drive(file_id, destination)
        except Exception as e:
            print(f"✗ Error descargando {file_name}: {e}")


if __name__ == "__main__":
    descargar_todos_los_archivos()
