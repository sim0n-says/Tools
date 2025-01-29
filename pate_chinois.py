import os
import html
import re
from bs4 import BeautifulSoup
import requests
from urllib.parse import quote
import xml.etree.ElementTree as ET

# URL de base et modèle de l'URL de recherche
base_url = "https://www.quebec.ca"
search_url_template = "https://www.quebec.ca/?id=23879&tx_solr[q]=*&tx_solr[filter][]=species_status:Menac%C3%A9e&tx_solr[filter][]=species_status:Susceptible%20d%E2%80%99%C3%AAtre%20d%C3%A9sign%C3%A9e%20comme%20menac%C3%A9e%20ou%20vuln%C3%A9rable&tx_solr[filter][]=species_status:Vuln%C3%A9rable&tx_solr[filter][]=species_status:Susceptible&tx_solr[sort]=alphaAsc%20asc&tx_solr[page]={page}&type=7382"

# Fonction pour obtenir le nombre total de pages
def get_total_pages(session):
    search_url = search_url_template.format(page=1)
    response = session.get(search_url)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')
    pagination_links = soup.find_all('a', class_='solr-ajaxified')
    max_page = max((int(link.get('data-page', 1)) for link in pagination_links), default=1)
    return max_page

# Fonction pour extraire les informations de la fiche
def extract_info(fiche_bio_info):
    info_dict = {}
    if fiche_bio_info:
        for p in fiche_bio_info.find_all('p'):
            strong_tag = p.find('strong')
            if strong_tag:
                key = strong_tag.get_text(strip=True)
                value = ''.join(sibling.strip() if isinstance(sibling, str) else sibling.get_text(strip=True) for sibling in strong_tag.next_siblings if sibling and (isinstance(sibling, str) or sibling.name in ['i', 'a']))
                info_dict[key] = html.escape(value.strip()) if value else 'N/A'
    return info_dict

# Fonction pour nettoyer les clés des dictionnaires
def clean_key(key):
    return re.sub(r'\W+', '_', key)

# Fonction pour traiter une fiche
def process_fiche(session, fiche_url):
    response = session.get(fiche_url)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')

    file_title_tag = soup.find('h1', id='titre-principal', class_='themeTitre')
    file_title = re.sub(r'\W+', '_', file_title_tag.get_text(strip=True) if file_title_tag else 'output')

    title = soup.find('h1').get_text(strip=True) if soup.find('h1') else 'N/A'
    description_tag = soup.find('div', class_='field--name-field-description')
    description = description_tag.get_text(strip=True) if description_tag else 'N/A'

    info_dict = {}
    for fiche_bio_info in soup.find_all('div', class_='ficheBio-info'):
        info_dict.update(extract_info(fiche_bio_info))

    content_elements = soup.find('div', class_='col-12 content-elements')
    if content_elements:
        for frame in content_elements.find_all('div', class_='frame'):
            header = frame.find('h2')
            if header:
                key = clean_key(header.get_text(strip=True))
                value = ''
                sub_info_dict = {}
                for sub_element in frame.find_all(['h3', 'p', 'ul']):
                    if sub_element.name == 'h3':
                        if value:
                            info_dict[key] = html.escape(value.strip()) if value else 'N/A'
                        sub_key = clean_key(sub_element.get_text(strip=True))
                        sub_value = ' '.join(p.get_text(strip=True) for p in sub_element.find_next_siblings(['p', 'ul']) if p.name in ['p', 'ul'])
                        sub_info_dict[sub_key] = html.escape(sub_value.strip()) if sub_value else 'N/A'
                    elif sub_element.name == 'p' and not sub_element.find_previous_sibling('h3'):
                        value += sub_element.get_text(strip=True) + ' '
                    elif sub_element.name == 'ul' and not sub_element.find_previous_sibling('h3'):
                        value += ' '.join(li.get_text(strip=True) for li in sub_element.find_all('li')) + ' '
                if value:
                    info_dict[key] = html.escape(value.strip()) if value else 'N/A'
                info_dict.update(sub_info_dict)

    return file_title, title, description, info_dict

# Créer un élément racine pour le fichier XML
root = ET.Element("faune")

# Utiliser une session pour les requêtes HTTP
with requests.Session() as session:
    # Ajouter l'en-tête User-Agent personnalisé
    session.headers.update({'User-Agent': 'SteakBléDindePatate/1.0 (Ce sondeur/collecteur est utilisé pour récupérer des données sur Québec.ca car le portail ne propose pas d''api acessible au public.)'})
    
    total_pages = get_total_pages(session)
    for page in range(1, total_pages + 1):
        print(f"Traitement de la page {page}")
        search_url = search_url_template.format(page=page)
        response = session.get(search_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        fiche_links = [base_url + link['href'] for link in soup.find_all('a', class_='espece-link', href=True) if link['href'].startswith('/agriculture-environnement-et-ressources-naturelles/faune/animaux-sauvages-quebec/fiches-especes-fauniques')]
        print(f"Nombre de fiches trouvées sur la page {page}: {len(fiche_links)}")

        for fiche_url in fiche_links:
            print(f"Traitement de la fiche: {fiche_url}")
            file_title, title, description, info_dict = process_fiche(session, fiche_url)

            fiche_element = ET.SubElement(root, "Nom_francais", name=file_title)
            ET.SubElement(fiche_element, "title").text = html.escape(title)
            ET.SubElement(fiche_element, "description").text = html.escape(description)
            fiche_bio_info_element = ET.SubElement(fiche_element, "ficheBioInfo")
            for key, value in info_dict.items():
                ET.SubElement(fiche_bio_info_element, clean_key(key)).text = value

# Fonction pour indenter le XML
def indent(elem, level=0):
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

# Indenter le XML
indent(root)

# Créer un arbre XML et écrire dans un fichier en UTF-8
tree = ET.ElementTree(root)
with open("faune_info.xml", "wb") as files:
    tree.write(files, encoding='utf-8', xml_declaration=True)

print("Les informations ont été extraites et enregistrées dans faune_info.xml")