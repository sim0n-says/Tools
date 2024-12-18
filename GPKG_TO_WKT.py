import geopandas as gpd
from shapely.geometry import box

# Fonction pour obtenir l'emprise en format WKT
def get_bounding_box_wkt(layer):
    # Obtenir l'emprise de la couche
    bounds = layer.total_bounds
    # Créer une géométrie d'emprise
    bbox = box(*bounds)
    # Retourner la représentation WKT de l'emprise
    return bbox.wkt

# Demander à l'utilisateur de fournir le chemin du fichier
file_path = input("Veuillez fournir le chemin du fichier: ")

# Charger la couche
layer = gpd.read_file(file_path)

# Reprojeter la couche en WGS84
layer = layer.to_crs(epsg=4326)

# Obtenir l'emprise en format WKT
bounding_box_wkt = get_bounding_box_wkt(layer)

# Afficher l'emprise en WKT
print(f"Bounding Box in WKT (WGS84): {bounding_box_wkt}")

# Sauvegarder l'emprise en WKT dans un fichier texte
with open('bounding_box_wkt.txt', 'w') as f:
    f.write(bounding_box_wkt)

print("Emprise en WKT sauvegardée dans bounding_box_wkt.txt")
