import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import os
import gc
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')

def explain_matches(cv_txt_path=None, matches_csv_path=None, progress_callback=None):
    """
    Explains matches between CV and Jobs using Qwen model.
    Results are cleaned to ensure single-line output per row in the CSV.
    """
    if cv_txt_path is None:
        cv_txt_path = os.path.join(DATA_DIR, "cv_synthesized.txt")
        
    # Determine which matches file to use
    if matches_csv_path is None:
        cross_path = os.path.join(DATA_DIR, "final_matches_cross.csv")
        simple_path = os.path.join(DATA_DIR, "final_matches.csv")
        
        if os.path.exists(cross_path):
            matches_csv_path = cross_path
            if progress_callback:
                progress_callback("Utilisation des résultats du Cross Matching (Etape 6).")
        elif os.path.exists(simple_path):
            matches_csv_path = simple_path
            if progress_callback:
                progress_callback("Utilisation des résultats du Matching Standard (Etape 5).")
        else:
            if progress_callback:
                progress_callback("❌ Erreur : Aucun fichier de matching trouvé. Veuillez lancer l'étape 5 ou 6.")
            return None

    if not os.path.exists(cv_txt_path):
        if progress_callback:
            progress_callback("❌ Erreur : Synthèse CV manquante. Veuillez lancer l'étape 4.")
        return None

    # 1. Read Data
    try:
        with open(cv_txt_path, 'r', encoding='utf-8') as f:
            cv_content = f.read()
        
        df_jobs = pd.read_csv(matches_csv_path)
        
    except Exception as e:
        if progress_callback:
            progress_callback(f"❌ Erreur lecture fichiers : {e}")
        return None

    # 2. Load Model
    model_name = "Qwen/Qwen2.5-1.5B-Instruct"
    if progress_callback:
        progress_callback(f"Chargement du modèle {model_name}...")
    
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype="auto",
            device_map="auto",
            low_cpu_mem_usage=True
        )
    except Exception as e:
        if progress_callback:
            progress_callback(f"❌ Erreur chargement modèle : {e}")
        return None

    explanations = []
    total_jobs = len(df_jobs)

    system_prompt = """Tu es un expert en recrutement et matching de talents.
    Ta mission est d'expliquer pourquoi un candidat correspond ou non à une offre d'emploi.
    Analyse les compétences techniques, l'expérience et le secteur.
    Sois concis, objectif et direct."""

    if progress_callback:
        progress_callback(f"Démarrage de l'analyse pour {total_jobs} offres...")

    for index, row in df_jobs.iterrows():
        job_title = row.get('Poste', 'Poste inconnu')
        company = row.get('Entreprise', 'Entreprise inconnue')
        job_desc = row.get('Resume_IA', '')
        
        user_prompt = f"""
        ANALYSE DE COMPATIBILITÉ
        
        CANDIDAT (Synthèse) :
        {cv_content}
        
        OFFRE D'EMPLOI ({job_title} chez {company}) :
        {job_desc}
        
        CONSIGNE :
        Explique en 3 points maximum pourquoi ce profil correspond ou non à cette offre. 
        Donne un verdict final : "Match Fort", "Match Partiel", ou "Pas de Match".
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        model_inputs = tokenizer([text], return_tensors="pt").to(model.device)
        
        generated_ids = model.generate(
            **model_inputs,
            max_new_tokens=1500, 
            temperature=0.3,
            top_p=0.9,
        )
        
        generated_ids = [
            output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]
        response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        
        # --- MODIFICATION ICI ---
        # Remplacement des sauts de ligne par des espaces pour tout garder sur une seule ligne
        response_single_line = response.replace('\n', ' ').replace('\r', ' ').strip()
        
        # Optionnel : retirer les doubles espaces créés par la suppression des retours à la ligne
        while '  ' in response_single_line:
            response_single_line = response_single_line.replace('  ', ' ')
            
        explanations.append(response_single_line)
        
        if progress_callback:
            progress_callback(f"[{index+1}/{total_jobs}] Analyse terminée pour {job_title}")

    df_jobs['Explanation'] = explanations
    
    output_path = os.path.join(DATA_DIR, 'explained_matches.csv')
    
    # escapechar permet de gérer proprement les caractères spéciaux si nécessaire, 
    # mais le nettoyage ci-dessus fait le gros du travail.
    df_jobs.to_csv(output_path, index=False, encoding='utf-8')
    
    if progress_callback:
        progress_callback("✅ Explications générées avec succès (Format ligne unique).")

    # Cleanup
    del model
    del tokenizer
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    gc.collect()

    return output_path