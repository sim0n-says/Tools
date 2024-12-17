# Ce script télécharge le fichier Excel des données d'espèces suivies part le CDPNQ, extrait les noms scientifiques,
# interroge l'API GBIF pour obtenir les occurrences géolocalisées au Québec, et enregistre les résultats
# dans des fichiers Excel et GeoPackage pour une analyse géospatiale ultérieure.

import os
import pandas as pd
import requests
import time
import geopandas as gpd
from shapely.geometry import Point
import re
from tqdm import tqdm

# Définir les limites géographiques pour le Québec
min_latitude = 45.0
max_latitude = 62.0
min_longitude = -79.5
max_longitude = -57.0


# URL du fichier Excel
excel_url = 'https://cdn-contenu.quebec.ca/cdn-contenu/faune/documents/precaire/LI-especes-suivies_CDPNQ.xlsx'

# Télécharger le fichier Excel
response = requests.get(excel_url)
with open('LI-especes-suivies_CDPNQ.xlsx', 'wb') as file:
    file.write(response.content)

# Lire le fichier Excel et traiter les deux feuilles
excel_file = 'LI-especes-suivies_CDPNQ.xlsx'
sheets = pd.read_excel(excel_file, sheet_name=None)

# Créer une liste pour stocker les résultats
results = []

# URL de base de l'API GBIF
gbif_api_url = "https://api.gbif.org/v1/occurrence/search"

try:
    for sheet_name, sheet_df in sheets.items():
        print(f"Traitement de la feuille: {sheet_name}")
        for index, row in tqdm(sheet_df.iterrows(), total=len(sheet_df), desc=f"Feuille {sheet_name}"):
            # Extraire le nom scientifique entre parenthèses dans la troisième colonne
            match = re.search(r'\(([^)]+)\)', row.iloc[2])
            if match:
                species_name = match.group(1)

                # Extraire les deux premiers mots du nom scientifique
                scientific_name_parts = species_name.split()
                if len(scientific_name_parts) >= 2:
                    search_name = f"{scientific_name_parts[0]} {scientific_name_parts[1]}"
                else:
                    search_name = species_name

                params = {
                    'scientificName': search_name,
                    'decimalLatitude': f"{min_latitude},{max_latitude}",
                    'decimalLongitude': f"{min_longitude},{max_longitude}"
                    #'stateProvince': 'Québec',  # Filtrer par la province du Québec
                    #'country': 'CA'  # Filtrer par le code pays du Canada
                }
                
                # Faire une requête à l'API GBIF
                response = requests.get(gbif_api_url, params=params)
                
                # Vérifier le statut de la réponse
                if response.status_code == 200:
                    try:
                        data = response.json()
                    except requests.exceptions.JSONDecodeError:
                        print(f"Erreur de décodage JSON pour l'espèce {species_name}. Contenu de la réponse : {response.text}")
                        continue
                else:
                    print(f"Erreur de requête pour l'espèce {species_name}. Statut de la réponse : {response.status_code}")
                    continue
                
                # Vérifier si des occurrences ont été trouvées
                if 'results' in data:
                    for occurrence in data['results']:
                        if 'decimalLatitude' in occurrence and 'decimalLongitude' in occurrence:
                            result = row.to_dict()  # Convertir la ligne actuelle en dictionnaire
                            result.update({
                                'Latitude': occurrence['decimalLatitude'],
                                'Longitude': occurrence['decimalLongitude']
                            })
                            results.append(result)
                
                # Pause d'une seconde entre chaque requête
                time.sleep(0.2)
except KeyboardInterrupt:
    print("Interruption du script détectée. Enregistrement des données...")
finally:
    # Convertir les résultats en DataFrame
    results_df = pd.DataFrame(results)

    # Enregistrer les résultats dans un nouveau fichier Excel
    results_df.to_excel('Fetch/coordonnees_especes.xlsx', index=False)

    # Convertir les résultats en GeoDataFrame
    gdf = gpd.GeoDataFrame(
        results_df, 
        geometry=[Point(xy) for xy in zip(results_df['Longitude'], results_df['Latitude'])],
        crs="EPSG:4326"
    )

    # Enregistrer les résultats dans un fichier GeoPackage
    gdf.to_file('Fetch/coordonnees_especes.gpkg', layer='especes', driver='GPKG')

    print(f"Traitement terminé. {len(results)} occurrences trouvées.")
    print("Les résultats ont été enregistrés dans 'Fetch/coordonnees_especes.xlsx' et '../coordonnees_especes.gpkg'.")
