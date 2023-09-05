import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

## OCR ####################
# im = Image.open("fantastique.jpg") # Ouverture du fichier image
# text = pytesseract.image_to_string(im)
# print(text)
## FIN OCR ###
# images = convert_from_path("numerise.pdf")
# print(images)
# Filtrage (augmentation du contraste)
# im = im.filter(ImageFilter.MedianFilter())
# enhancer = ImageEnhance.Contrast(im)
# im = enhancer.enhance(2)
# im = im.convert('1')
# # # Lancement de la procédure de reconnaissance





import pdfplumber
import os


# Chemin vers le fichier PDF que vous souhaitez extraire
pdf_file_path = "numerise2.pdf"

# Créez un répertoire pour stocker les images extraites
output_directory = "images_extraites"
os.makedirs(output_directory, exist_ok=True)

# Ouvrez le fichier PDF
with pdfplumber.open(pdf_file_path) as pdf:
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
            text = pytesseract.image_to_string(image)
            print(f"Texte extrait de l'image {img_index + 1} de la page {page_number + 1}:\n{text}\n")

print("Extraction des images terminée. Les images sont enregistrées dans le répertoire", output_directory)