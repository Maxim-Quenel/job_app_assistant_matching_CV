import pandas as pd
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import os
import gc

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')

def rewrite_jobs(input_csv_path=None, progress_callback=None):
    """
    Rewrites job descriptions using Qwen model.
    """
    if input_csv_path is None:
        input_csv_path = os.path.join(DATA_DIR, "jobs_raw.csv")
    
    if not os.path.exists(input_csv_path):
        if progress_callback:
            progress_callback("❌ Erreur : Fichier jobs_raw.csv non trouvé. Veuillez lancer l'étape 1.")
        return None

    # 1. Load Model
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

    # 2. Load Data
    try:
        df = pd.read_csv(input_csv_path)
    except Exception as e:
         if progress_callback:
            progress_callback(f"❌ Erreur lecture CSV : {e}")
         return None
         
    resumes_stockes = []
    
    if progress_callback:
        progress_callback(f"Début de la réécriture pour {len(df)} offres.")

    for index, row in df.iterrows():
        msg = f"Traitement de l'offre {index + 1}/{len(df)} : {row['Poste']}"
        if progress_callback:
            progress_callback(msg)
        else:
            print(msg)

        prompt = f"""Tu es un expert en recrutement. Analyse l'offre d'emploi ci-dessous et génère un résumé structuré.
        
        Données de l'offre :
        - Poste : {row['Poste']}
        - Entreprise : {row['Entreprise']}
        - Lieu : {row['Lieu']}
        - Missions : {row['Missions']}
        - Profil Recherché : {row['Profil_Recherche']}




        Génère la réponse uniquement sous ce format strict :
        RESUME_MATCHING:
        - Type de profil recherché
        - compétences clés: [Liste]
        - Soft_Skills: [Liste]
        - Seniority: [Niveau]
        - Core_Mission: [Phrase résumée]
        """

        messages = [
            {"role": "system", "content": "Tu es un assistant utile."},
            {"role": "user", "content": prompt}
        ]

        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

        generated_ids = model.generate(
            **model_inputs,
            max_new_tokens=500,
            temperature=0.1,
            do_sample=True
        )
        
        generated_ids = [
            output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]
        response_text = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        
        clean_response = response_text.replace('RESUME_MATCHING:', '').strip()
        clean_response_oneline = clean_response.replace('\n', ' | ').replace('\r', '')

        resumes_stockes.append(clean_response_oneline)

    df['Resume_IA'] = resumes_stockes
    output_path = os.path.join(DATA_DIR, 'jobs_rewritten.csv')
    df.to_csv(output_path, index=False)
    
    if progress_callback:
        progress_callback("✅ Réécriture terminée. Libération de la mémoire...")
    
    # Cleanup memory
    del model
    del tokenizer
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    gc.collect()
    
    return output_path
