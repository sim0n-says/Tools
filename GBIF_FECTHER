import os
import time
from pygbif import occurrences as occ

try:
    # Demander à l'utilisateur de saisir ses variables d'environnement
    os.environ['GBIF_USER'] = input("Veuillez saisir votre nom d'utilisateur GBIF: ")
    os.environ['GBIF_PWD'] = input("Veuillez saisir votre mot de passe GBIF: ")
    os.environ['GBIF_EMAIL'] = input("Veuillez saisir votre email GBIF: ")

    query = {
        "type": "and",
        "predicates": [
            {
                "type": "isNotNull",
                "parameter": "YEAR"
            },
            {
                "type": "not",
                "predicate": {
                    "type": "in",
                    "key": "ISSUE",
                    "values": ["RECORDED_DATE_INVALID", "TAXON_MATCH_FUZZY", "TAXON_MATCH_HIGHERRANK"]
                }
            },
            {
                "type": "in",
                "key": "BASIS_OF_RECORD",
                "values": ["OBSERVATION", "HUMAN_OBSERVATION", "OCCURRENCE"]
            },
            {
                "type": "equals",
                "key": "COUNTRY",
                "value": "CA"
            },
            {
                "type": "equals",
                "key": "HAS_COORDINATE",
                "value": "true"
            },
            {
                "type": "equals",
                "key": "HAS_GEOSPATIAL_ISSUE",
                "value": "false"
            },
            {
                "type": "within",
                "geometry": "POLYGON((-56.93492688561576 44.99135832579372, -56.93492688561576 62.58246570128598, -79.76532426607646 62.58246570128598, -79.76532426607646 44.99135832579372, -56.93492688561576 44.99135832579372))"
            },
            {
                "type": "in",
                "key": "IUCN_RED_LIST_CATEGORY",
                "values": ["NT", "VU", "EN", "CR"]
            }
        ]
    }

    # Obtenir la clé de téléchargement
    download_key = occ.download(query)
    print(f"Your download key is {download_key}")

    # Extraire la clé de téléchargement du tuple
    download_key = download_key[0] if isinstance(download_key, tuple) else download_key

    # Vérifier périodiquement l'état du téléchargement
    status = occ.download_meta(download_key)['status']
    while status in ['PREPARING', 'RUNNING']:
        print(f"Download status: {status}. Waiting for 30 seconds...")
        time.sleep(30)
        status = occ.download_meta(download_key)['status']

    if status == 'SUCCEEDED':
        # Créer le répertoire de téléchargement s'il n'existe pas
        download_dir = os.path.join(os.path.dirname(__file__), 'downloads')
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        
        # Télécharger les données
        download_path = os.path.join(download_dir, f'{download_key}.zip')
        occ.download_get(download_key, path=download_path)
        print("Download completed successfully.")
    else:
        print(f"Download failed with status: {status}")

except KeyboardInterrupt:
    print("\nOpération interrompue par l'utilisateur.")
except Exception as e:
    print(f"Une erreur est survenue: {e}")
