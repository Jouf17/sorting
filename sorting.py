import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PyPDF2 import PdfReader
import locale
from datetime import datetime
import json
import pytesseract
import pdfplumber
import shutil
import random
import re

from nomDossier import dossier_surveillance
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Charger les mots-clés depuis le fichier de configuration
with open("config.json") as config_file:
    config = json.load(config_file)

mots_cles_employeur = config["mots_cles"]["employeur"]
mots_cles_type_document = config["mots_cles"]["type_document"]

# Obtenez les permissions actuelles du dossier
permissions_actuelles = os.stat(dossier_surveillance).st_mode

# Calculez les nouvelles permissions en ajoutant les bits d'autorisation
nouvelles_permissions = permissions_actuelles | 0o777

# Appliquez les nouvelles permissions au dossier
os.chmod(dossier_surveillance, nouvelles_permissions)

locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
attendreAnalyseOcr = False
def ocr_termine():
    global attendreAnalyseOcr
    attendreAnalyseOcr = True

class MonEventHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(".pdf"):
            pdf_path = event.src_path
            analyse_pdf(pdf_path)

def analyse_pdf(pdf_path):
    try:
        with open(pdf_path, "rb") as fichier_pdf:
            pdf = PdfReader(fichier_pdf)
            
            # Extraire la date du document
            O_date_document = extraire_date_document(pdf)
            print(O_date_document, "date création pdt")
            texte_pdf = ""
            for page_num in range(len(pdf.pages)):
                page = pdf.pages[page_num]
                texte_pdf += page.extract_text()

        fichier_pdf.close()
        
        if texte_pdf == "":
            texte_ocr = analyseOcr(pdf_path, ocr_termine) 
            texte_pdf = texte_ocr
            date_texte = recherche_date_dans_texte(texte_pdf)
            if date_texte:
                O_date_document = date_texte
            nouveau_chemin = trier_fichier_pdf(texte_pdf, O_date_document)   
            shutil.copy(pdf_path, nouveau_chemin)
        else:
            date_texte = recherche_date_dans_texte(texte_pdf)
            if date_texte:
                O_date_document = date_texte
            nouveau_chemin = trier_fichier_pdf(texte_pdf, O_date_document)   
            os.rename(pdf_path, nouveau_chemin)            
    
    except Exception as e:
        print("Une erreur s'est produite lors de l'analyse du PDF : {}".format(str(e)))

    

def trier_fichier_pdf(texte, O_date_document):
    nb_mots_max_type_doc = 0
    nb_mots_max_type_employeur = 0
    employeur_nom = "Employeur_Inconnu"
    type_document = "X)Type_Document_Inconnu"

    # Tri de la date
    annee = O_date_document.strftime("%Y")
    dossier_annee = os.path.join(dossier_surveillance, annee)

    if not os.path.exists(dossier_annee):
        os.makedirs(dossier_annee)
    
    numero_mois = O_date_document.month
    mois = O_date_document.strftime("%B").capitalize()
    mois = f"{numero_mois}_{mois}"
    dossier_mois = os.path.join(dossier_annee, mois)
    
    if not os.path.exists(dossier_mois):
        os.makedirs(dossier_mois)

    for employeur, mots_cles in mots_cles_employeur.items():
        nb_mots_employeur = 0
        for mot in mots_cles:
            if mot.lower() in texte.lower():
                nb_mots_employeur += 1

        if nb_mots_employeur > nb_mots_max_type_employeur:
            nb_mots_max_type_employeur = nb_mots_employeur
            employeur_nom = employeur
    
    dossier_employeur = os.path.join(dossier_mois, employeur_nom)
    if not os.path.exists(dossier_employeur):
        os.makedirs(dossier_employeur)
    
    # Tri du type
    for theme, mots_cles in mots_cles_type_document.items():
        nb_mots_theme = 0
        for mot in mots_cles:
            if mot.lower() in texte.lower():
                nb_mots_theme += 1

        if nb_mots_theme > nb_mots_max_type_doc:
            nb_mots_max_type_doc = nb_mots_theme
            type_document = theme

    nom_fichier = type_document[:2] + O_date_document.strftime("%d_%m_%Y") + '.pdf'
    
    dossier_type_document = os.path.join(dossier_employeur, type_document)
    if not os.path.exists(dossier_type_document):
        os.makedirs(dossier_type_document)
    
    nouveau_chemin = os.path.join(dossier_type_document, nom_fichier) 
    
    nouveau_chemin = renommer_pdf(nouveau_chemin, dossier_type_document)
    
    return nouveau_chemin        

def extraire_date_document(pdf):
    date_str = pdf.metadata.get('/CreationDate')
    if date_str:
        date = datetime.strptime(date_str[2:10], "%Y%m%d")
        return date
    return None

def analyseOcr(pdf_file_path, callback):
    global attendreAnalyseOcr
    # Créez un répertoire pour stocker les images extraites
    output_directory = "images_extraites"
    os.makedirs(output_directory, exist_ok=True)

    pdf = None  # Initialisation du lecteur PDF en dehors du bloc try

    try:
        with pdfplumber.open(pdf_file_path) as pdf:
            # Ouvrez le fichier PDF
            texte_pdf = ""
            # Parcourez chaque page du PDF
            for page_number in range(len(pdf.pages)):
                page = pdf.pages[page_number]

                # Parcourez les images sur la page
                for img_index, img in enumerate(page.images):
                    x0, y0, x1, y1 = img["x0"], img["y0"], img["x1"], img["y1"]

                    # Convertir PageImage en image Pillow
                    page_image = page.to_image()

                    # Obtenir l'image entière de la page
                    full_page_image = page_image.original

                    # Découper la région de l'image
                    image = full_page_image.crop((x0, y0, x1, y1))

                    # Enregistrez l'image extraite dans le répertoire de sortie
                    image_file_path = os.path.join(output_directory, f"page_{page_number + 1}_img_{img_index + 1}.png")
                    image.save(image_file_path, "PNG")

                    # Utiliser pytesseract pour extraire du texte de l'image
                    texte_pdf += pytesseract.image_to_string(image)

        for fichier in os.listdir(output_directory):
            path = os.path.join(output_directory, fichier)
            if os.path.isfile(path):
                os.remove(path)

        
        # os.system(f"taskkill /F /IM pdfplumber.exe")
        
        # for fichier in os.listdir(dossier_surveillance):
        #     path = os.path.join(dossier_surveillance, fichier)
        #     if os.path.isfile(path):
        #         os.remove(path)

        pdf.close()
        callback()
        return texte_pdf
    except pytesseract.pytesseract.TesseractError as e:
        print("Erreur lors de l'OCR : {}".format(str(e)))
        # Ajoutez ici la gestion de l'erreur d'OCR, par exemple, en arrêtant proprement le processus
        raise  # Propagez l'erreur pour qu'elle soit gérée en amont
    except pdfplumber.PDFSyntaxError as e:
        print("Erreur de syntaxe PDF : {}".format(str(e)))
    except pdfplumber.PageObjectCreationError as e:
        print("Erreur de création d'objet de page : {}".format(str(e)))
    except Exception as e:
        print("Une erreur inattendue s'est produite : {}".format(str(e)))
    finally:
        if pdf is not None:
            pdf.close()  # Assurez-vous que le document PDF est fermé, même en cas d'erreur

def renommer_pdf(fichier, dossier):
  """
  Renomme le nouveau fichier PDF avec une incrémentation si nécessaire.

  Args:
    fichier: Le chemin du nouveau fichier PDF à renommer.
    dossier: Le chemin du dossier dans lequel le fichier est situé.

  Returns:
    Le nouveau chemin du fichier PDF.
  """

  # Vérifie si le fichier existe déjà dans le dossier.
  if os.path.exists(os.path.join(dossier, fichier)):
    
    hash = "".join(random.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(5))
    # Renomme le fichier.
    nouveau_nom = f"{fichier[:-4]}({hash}).pdf"

    # Retourne le nouveau chemin du fichier.
    return nouveau_nom
  else:
    # Le fichier n'existe pas déjà, on retourne le chemin d'origine.
    return fichier

def recherche_date_dans_texte(texte_pdf):
    date = False
    
    patterns = [
        r'\b\d{2}/\d{2}/\d{4}\b',
        r'\b\d{2}/\d{2}/\d{2}\b',
        r'\b\d{2}/\d{4}\b',
        r'\b\d{2}/\d{2}\b',
        r'\b\d{2} \d{2} \d{4}\b'
    ]
    for pattern in patterns:
        match = re.search(pattern, texte_pdf)
        if match:
            date = match.group()
            break

    if date:
        if "/" in date:
            date_parts = date.split('/')
        elif " " in date:
            date_parts = date.split(' ')
        else:
            raise ValueError("Format de date invalide")
        
        if len(date_parts) == 3:
            jour = int(date_parts[0])
            mois = int(date_parts[1])
            annee = int(date_parts[2])
        elif len(date_parts) == 2:
            jour = 1  # Jour par défaut s'il est manquant
            mois = int(date_parts[0])
            annee = int(date_parts[1])
        else:
            raise ValueError("Format de date invalide")
        if annee < 1000:
            annee += 2000
        date_convertie = datetime(annee, mois, jour).date()
        date = date_convertie.strftime("%d/%m/%Y")
        date = datetime.strptime(date, "%d/%m/%Y").date()
        print(date, "date avant traitement")
        if date.year >= 2012 and date.year <= 2050:
            O_date_document = date
        else:
            O_date_document = False
    else:
        O_date_document = False
    print(O_date_document, "date dans texte")
    return O_date_document

# Instanciation de l'observateur et de l'événement
observer = Observer()
event_handler = MonEventHandler()

# Ajout du dossier à surveiller à l'observateur
observer.schedule(event_handler, dossier_surveillance, recursive=False)

for fichier in os.listdir(dossier_surveillance):
    path = os.path.join(dossier_surveillance, fichier)
    if os.path.isfile(path):
        os.remove(path)

# Démarrage de l'observateur
observer.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()

# Arrêt de l'observateur lorsque vous souhaitez terminer le script
observer.join()

