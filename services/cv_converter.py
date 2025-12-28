import pdfplumber
import re
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')

def nettoyer_texte_avance(texte: str) -> str:
    """
    Nettoie les artefacts courants d'extraction PDF.
    """
    if not texte:
        return ""

    def replacer_lettres_isolees(match):
        return match.group(0).replace(" ", "")
    
    texte = re.sub(r'(?:\b[A-Za-z0-9À-ÿ]\s){3,}[A-Za-z0-9À-ÿ]\b', replacer_lettres_isolees, texte)
    texte = re.sub(r'\n\s*\n', '\n\n', texte)
    texte = re.sub(r'[ \t]+', ' ', texte)

    return texte.strip()

def convert_cv_to_txt(pdf_path, progress_callback=None):
    """
    Converts PDF CV to TXT.
    """
    if not os.path.exists(pdf_path):
        if progress_callback:
            progress_callback(f"❌ Erreur : Fichier PDF inconnu : {pdf_path}")
        return None

    if progress_callback:
        progress_callback(f"Traitement de la conversion PDF : {os.path.basename(pdf_path)}")

    texte_global = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                if progress_callback:
                    progress_callback("⚠️ Le PDF semble vide.")
                return None

            for i, page in enumerate(pdf.pages):
                texte_page = page.extract_text(x_tolerance=2, y_tolerance=2)
                if texte_page:
                    texte_global += f"\n--- PAGE {i+1} ---\n"
                    texte_global += nettoyer_texte_avance(texte_page)
                else:
                    if progress_callback:
                        progress_callback(f"⚠️ Page {i+1} : Aucun texte sélectionnable.")
    except Exception as e:
        if progress_callback:
            progress_callback(f"❌ Erreur lecture PDF : {e}")
        return None

    output_path = os.path.join(DATA_DIR, "cv_converted.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(texte_global)
    
    if progress_callback:
        progress_callback(f"✅ Conversion terminée : {output_path}")
    
    return output_path
