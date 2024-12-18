import csv
import json

def load_iucn_list(filename):
    iucn_dict = {}
    with open(filename, mode='r', encoding='utf-8') as file:
        data = json.load(file)
        for entry in data['result']:
            species_name = entry['scientific_name'].strip().lower()
            iucn_dict[species_name] = entry['category']
    return iucn_dict

def normalize_species_name(name):
    return name.strip().lower()

def compare_species(csv_file, json_file, output_file):
    iucn_list = load_iucn_list(json_file)
    found_species = []
    not_found_species = []

    with open(csv_file, mode='r', newline='', encoding='utf-8') as infile, open(output_file, mode='w', newline='', encoding='utf-8') as outfile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames + ['category']
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            species_name = normalize_species_name(row.get('species', row.get('scientificName', '')))
            if species_name in iucn_list:
                row['category'] = iucn_list[species_name]
                found_species.append(species_name)
            else:
                row['category'] = 'Not Found'
                not_found_species.append(species_name)
            writer.writerow(row)
    
    return found_species, not_found_species

if __name__ == "__main__":
    found, not_found = compare_species('species.csv', 'CA.json', 'species_with_category.csv')
    print(f"Espèces trouvées: {found}")
    print(f"Espèces non trouvées: {not_found}")
