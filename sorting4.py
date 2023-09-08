##TODO : faire la rechercher avec l'ocr numérisé
##TODO : essayer de trouver la date dans le doc en prio

import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PyPDF2 import PdfReader
import locale
from datetime import datetime
import json
import sys
from nomDossier import dossier_surveillance

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

            texte_pdf = ""
            for page_num in range(len(pdf.pages)):
                page = pdf.pages[page_num]
                texte_pdf += page.extract_text()

            nouveau_chemin = trier_fichier_pdf(pdf_path, texte_pdf, O_date_document)

            fichier_pdf.close()
            os.rename(pdf_path, nouveau_chemin)
            # print("Le fichier {} a été déplacé vers le dossier {}".format(nouveau_chemin))
    
    except Exception as e:
        print("Une erreur s'est produite lors de l'analyse du PDF : {}".format(str(e)))

def trier_fichier_pdf(pdf_path, texte, O_date_document):
    nb_mots_max = 0
    employeur_nom = "Autre"
    type_document = "X)Pas_de_type"

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

    # Tri de l'employeur
    for mot in mots_cles_employeur:
        if mot.lower() in texte.lower():
            employeur_nom = mot
            break

    dossier_employeur = os.path.join(dossier_mois, employeur_nom)
    if not os.path.exists(dossier_employeur):
        os.makedirs(dossier_employeur)

    # Tri du type
    for theme, mots_cles in mots_cles_type_document.items():
        nb_mots_theme = 0
        for mot in mots_cles:
            if mot.lower() in texte.lower():
                nb_mots_theme += 1

        if nb_mots_theme > nb_mots_max:
            nb_mots_max = nb_mots_theme
            type_document = theme

    nom_fichier = type_document[:2] + O_date_document.strftime("%d_%m_%Y") + '.pdf'

    dossier_type_document = os.path.join(dossier_employeur, type_document)
    if not os.path.exists(dossier_type_document):
        os.makedirs(dossier_type_document)

    nouveau_chemin = os.path.join(dossier_type_document, nom_fichier) 

    return nouveau_chemin        

def extraire_date_document(pdf):
    date_str = pdf.metadata.get('/CreationDate')
    if date_str:
        date = datetime.strptime(date_str[2:10], "%Y%m%d")
        return date
    return None

# Instanciation de l'observateur et de l'événement
observer = Observer()
event_handler = MonEventHandler()

# Ajout du dossier à surveiller à l'observateur
observer.schedule(event_handler, dossier_surveillance, recursive=False)

# Démarrage de l'observateur
observer.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()

# Arrêt de l'observateur lorsque vous souhaitez terminer le script
observer.join()
