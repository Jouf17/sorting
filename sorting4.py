import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PyPDF2 import PdfReader
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
            date_document = extraire_date_document(pdf)

            texte = ""
            for page_num in range(len(pdf.pages)):
                page = pdf.pages[page_num]
                texte += page.extract_text()

            employeur_trouve = False
            
            for mot in mots_cles_employeur:
                if mot.lower() in texte.lower():
                    employeur_trouve = True
                    fichier_pdf.close()
                    trier_fichier_pdf(pdf_path, mot, texte, date_document)
                    break

            if not employeur_trouve:
                fichier_pdf.close()
                trier_fichier_pdf(pdf_path, "Autre", texte, date_document)
    
    except Exception as e:
        print("Une erreur s'est produite lors de l'analyse du PDF : {}".format(str(e)))

def trier_fichier_pdf(pdf_path, employeur, texte, date_document):
    nom_fichier = os.path.basename(pdf_path)
    dossier_employeur = os.path.join(dossier_surveillance, employeur)
    dossier_type_document = ""
    nb_mots_max = 0

    for theme, mots_cles in mots_cles_type_document.items():
                nb_mots_theme = 0
                for mot in mots_cles:
                    if mot.lower() in texte.lower():
                        nb_mots_theme += 1

                if nb_mots_theme > nb_mots_max:
                    nb_mots_max = nb_mots_theme
                    dossier_type_document = theme

    if dossier_employeur:
        # Vérifier si le dossier employeur existe, sinon le créer
        if not os.path.exists(dossier_employeur):
            os.makedirs(dossier_employeur)

        if dossier_type_document:
            dossier_type_document_employeur = os.path.join(dossier_employeur, dossier_type_document)
            # Vérifier si le dossier type de document existe dans le dossier employeur, sinon le créer
            if not os.path.exists(dossier_type_document_employeur):
                os.makedirs(dossier_type_document_employeur)

            # Trier le fichier PDF par année et mois
            if date_document:
                annee = date_document.strftime("%Y")
                mois = date_document.strftime("%m")

                # Créer les dossiers pour l'année et le mois
                dossier_annee = os.path.join(dossier_type_document_employeur, annee)
                if not os.path.exists(dossier_annee):
                    os.makedirs(dossier_annee)
                
                dossier_mois = os.path.join(dossier_annee, mois)
                if not os.path.exists(dossier_mois):
                    os.makedirs(dossier_mois)

                # Déplacer le fichier PDF dans le dossier de l'année et du mois correspondants
                nouveau_chemin = os.path.join(dossier_mois, nom_fichier)
            else:
             nouveau_chemin = os.path.join(dossier_type_document_employeur, nom_fichier)    
        else:
            # Déplacer le fichier PDF dans le dossier employeur
            nouveau_chemin = os.path.join(dossier_employeur, nom_fichier)

        os.rename(pdf_path, nouveau_chemin)
        print("Le fichier {} a été déplacé vers le dossier {}".format(nom_fichier, nouveau_chemin))

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
