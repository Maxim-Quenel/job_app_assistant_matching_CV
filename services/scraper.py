import time
import pandas as pd
import urllib.parse
import re
import os
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By

# Ensure data directory exists
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# --- 1. FONCTION DE NETTOYAGE ---
def clean_text(text):
    if not isinstance(text, str):
        return str(text) if text is not None else ""
    text = text.replace('\n', ' ').replace('\r', ' ')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

# --- 2. FONCTION POUR SÉPARER LE TEXTE ---
def extract_mission_profil(full_text):
    if not full_text:
        return "", ""

    # 1. Nettoyage du "Header" (Navigation, Login, etc.)
    # On cherche un marqueur fort de début de description
    start_markers = ["les missions du poste", "le poste", "description du poste", "à propos du poste", "vos missions"]
    text_lower = full_text.lower()
    
    start_index = 0
    for marker in start_markers:
        idx = text_lower.find(marker)
        if idx != -1:
            # On prend le premier marqueur trouvé comme début réel
            start_index = idx
            break
            
    # Si on a trouvé un marqueur, on coupe tout ce qu'il y a avant
    if start_index > 0:
        relevant_text = full_text[start_index:]
    else:
        relevant_text = full_text

    text_lower = relevant_text.lower()
    
    # 2. Séparation Mission / Profil
    profil_keywords = ["le profil recherché", "ce que nous recherchons", "votre profil", "profil attendu", "profil"]
    
    split_index = -1
    for keyword in profil_keywords:
        idx = text_lower.find(keyword)
        # On s'assure que le mot clé n'est pas au tout début (titre)
        if idx != -1 and idx > 10: 
            split_index = idx
            break
    
    if split_index != -1:
        missions = relevant_text[:split_index]
        profil = relevant_text[split_index:]
    else:
        # Fallback si pas de séparation nette
        if len(relevant_text) > 500:
            missions = relevant_text
            profil = "Non séparé automatiquement (voir colonne Missions)"
        else:
            missions = relevant_text
            profil = ""
        
    return clean_text(missions), clean_text(profil)

# --- 3. GESTION DES COOKIES ---
def handle_cookies(driver):
    try:
        time.sleep(1)
        # Tente de trouver le bouton "Continuer sans accepter" ou "Refuser"
        buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Continuer sans') or contains(text(), 'Refuser') or contains(@id, 'close')]")
        if buttons:
            driver.execute_script("arguments[0].click();", buttons[0])
    except:
        pass

# --- 4. DÉPLIER LE PROFIL (CRUCIAL) ---
def expand_profil_section(driver):
    """
    Cherche le bouton/header 'Profil recherché' et force le clic via JS.
    """
    try:
        # On cherche un élément visible contenant "Profil"
        targets = driver.find_elements(By.XPATH, "//*[contains(text(), 'Profil') or contains(text(), 'profil')]")
        
        for target in targets:
            # On clique uniquement si c'est un titre pertinent (h2, h3, button, span dans un header)
            tag_name = target.tag_name.lower()
            text_cont = target.text.lower()
            
            if ("recherché" in text_cont or "attendu" in text_cont) and tag_name in ['h2', 'h3', 'h4', 'span', 'button', 'div']:
                driver.execute_script("arguments[0].click();", target)
                time.sleep(0.5) # Laisser le temps à l'animation
                break # Un seul clic suffit généralement
    except Exception:
        pass

# --- 5. FONCTION PRINCIPALE ---
def scrape_jobs(keyword, num_jobs=10, progress_callback=None):
    if progress_callback:
        progress_callback(f"🚀 Démarrage de la recherche pour : {keyword}")
    
    # Check if keyword is a URL
    if keyword.strip().startswith('http'):
        url = keyword.strip()
        # Decode url to try to guess a proper "keyword" for logging (optional)
        try:
             # simple heuristic to find 'k=' param or just use full url
             parsed = urllib.parse.urlparse(url)
             qs = urllib.parse.parse_qs(parsed.query)
             if 'k' in qs:
                 progress_callback(f"🔗 URL détectée. Mot-clé extrait : {qs['k'][0]}")
             else:
                 progress_callback(f"🔗 URL directe détectée.")
        except:
             pass
    else:
        encoded_keyword = urllib.parse.quote_plus(keyword)
        url = f"https://www.hellowork.com/fr-fr/emploi/recherche.html?k={encoded_keyword}"
    
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    # Edge Driver Path (Root of workspace)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    driver_path = os.path.join(project_root, "msedgedriver.exe")
    
    service = webdriver.edge.service.Service(driver_path) if os.path.exists(driver_path) else None
    
    # Init driver
    if service:
        driver = webdriver.Edge(options=options, service=service)
    else:
        driver = webdriver.Edge(options=options)

    all_jobs_data = []
    
    try:
        # --- PHASE 1 : LINK & LOCATION SCRAPING ---
        if progress_callback:
            progress_callback("1️⃣  Récupération des liens et lieux...")
        
        driver.get(url)
        time.sleep(3)
        handle_cookies(driver)
        
        job_links = []
        
        # --- DETECTION: Is this a Single Job Page? ---
        # Hueristic: URL contains /emplois/ and .html, or we find a "Postuler" button immediately
        is_single_job = False
        if "/emplois/" in url and ".html" in url:
             is_single_job = True
        
        if is_single_job:
            try:
                # Extract basic info from the opened page
                # These selectors are approximative and might need adjustment based on HelloWork's specific DOM for job pages
                
                # Title often in h1
                raw_title = driver.find_element(By.TAG_NAME, "h1").text
                
                # Company often in a span or div near title, or we can just leave it blank and let Phase 2 refine it?
                # Actually Phase 2 re-visits the link, so we just need a valid 'link' entry.
                # But Phase 2 expects 'Poste', 'Entreprise', 'Lieu' to log progress.
                
                raw_company = "Voir détail"
                raw_location = "Voir détail"
                
                # Attempt to find company/location from metadata if easier
                # But to be safe and simple:
                job_links.append({
                    "Poste": clean_text(raw_title),
                    "Entreprise": raw_company,
                    "Lieu": raw_location,
                    "Lien": url
                })
                
                if progress_callback:
                    progress_callback("✅ URL offre unique détectée.")
                    
            except Exception as e:
                # Fallback if detection failed or selectors changed
                 if progress_callback:
                    progress_callback(f"⚠️ Tentative lecture offre unique échouée: {e}")
        else:
            # --- STANDARD SEARCH RESULTS SCRAPING ---
            potential_jobs = driver.find_elements(By.CSS_SELECTOR, "ul > li")
            
            for card in potential_jobs:
                if len(job_links) >= num_jobs: break
                try:
                    # Check for h3 title
                    if card.find_elements(By.TAG_NAME, "h3"):
                        link_elem = card.find_element(By.TAG_NAME, "a")
                        link = link_elem.get_attribute("href")
                        
                        # Raw text extraction
                        raw_title = card.find_element(By.TAG_NAME, "h3").text.split('\n')[0]
                        txt_lines = card.text.split('\n')
                        
                        # Heuristique pour l'entreprise et le lieu
                        raw_company = txt_lines[1] if len(txt_lines) > 1 else "N/A"
                        
                        # RÉCUPÉRATION DU LIEU ICI
                        raw_location = "N/A"
                        if len(txt_lines) > 2:
                            potential_loc = txt_lines[2]
                            if len(potential_loc) < 50:
                                raw_location = potential_loc
                        
                        job_links.append({
                            "Poste": clean_text(raw_title),
                            "Entreprise": clean_text(raw_company),
                            "Lieu": clean_text(raw_location),
                            "Lien": link
                        })
                except Exception as e:
                    continue
            
        if progress_callback:
            progress_callback(f"✅ {len(job_links)} offres trouvées. Analyse détaillée...")
        
        # --- PHASE 2 : DETAILED SCRAPING ---
        for index, job in enumerate(job_links):
            msg = f"Traitement {index + 1}/{len(job_links)} : {job['Poste']} - {job['Lieu']}"
            if progress_callback:
                progress_callback(msg)
            else:
                print(msg)
            
            try:
                driver.get(job['Lien'])
                time.sleep(2) 
                handle_cookies(driver)

                # Clic pour ouvrir le profil (Improved)
                expand_profil_section(driver)
                
                # Récupération du texte (Improved)
                try:
                    full_desc_elem = driver.find_element(By.TAG_NAME, "main")
                    full_desc = full_desc_elem.text
                except:
                    full_desc = driver.find_element(By.TAG_NAME, "body").text

                missions, profil = extract_mission_profil(full_desc)
                
                # Rescue Fallback
                if len(profil) < 20:
                    try:
                        xpath_rescue = "//*[contains(text(), 'Profil')]/following-sibling::div"
                        profil_elem = driver.find_element(By.XPATH, xpath_rescue)
                        profil = clean_text(profil_elem.text)
                    except:
                        pass

                all_jobs_data.append({
                    "Poste": job['Poste'],
                    "Entreprise": job['Entreprise'],
                    "Lieu": job['Lieu'],
                    "Missions": missions,
                    "Profil_Recherche": profil,
                    "Lien": job['Lien']
                })
                
            except Exception as e:
                if progress_callback:
                    progress_callback(f"❌ Erreur sur {job['Poste']} : {e}")
                job_fallback = job.copy()
                job_fallback["Missions"] = "Erreur accès"
                job_fallback["Profil_Recherche"] = ""
                all_jobs_data.append(job_fallback)

    except Exception as e:
        if progress_callback:
            progress_callback(f"❌ Erreur critique : {e}")
        
    finally:
        driver.quit()
        if progress_callback:
            progress_callback("✅ Scraping terminé.")

    df = pd.DataFrame(all_jobs_data)
    output_path = os.path.join(DATA_DIR, "jobs_raw.csv")
    df.to_csv(output_path, index=False, encoding='utf-8-sig', sep=',')
    
    return output_path
