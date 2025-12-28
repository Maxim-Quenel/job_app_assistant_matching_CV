import pandas as pd
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import os
import gc
import json

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')

def parse_raw_job_text(raw_text, progress_callback=None):
    """
    Parses raw job text into structured data (Poste, Entreprise, Lieu, Missions, Profil) using Qwen.
    """
    
    if not raw_text or len(raw_text.strip()) < 10:
        if progress_callback:
            progress_callback("❌ Erreur : Texte fourni trop court.")
        return None

    # 1. Load Model
    model_name = "Qwen/Qwen2.5-1.5B-Instruct"
    if progress_callback:
        progress_callback(f"Chargement du modèle {model_name} pour analyse...")
    
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype="auto",
            device_map="auto"
        )
    except Exception as e:
        if progress_callback:
            progress_callback(f"❌ Erreur chargement modèle : {e}")
        return None

    # 2. Prompting
    if progress_callback:
        progress_callback("🧠 Analyse sémantique de l'annonce...")

    system_prompt = "Tu es un assistant spécialisé dans l'extraction de données d'offres d'emploi."
    user_prompt = f"""
    Analyse le texte de l'annonce ci-dessous et extrais les informations suivantes au format JSON strict.
    
    Champs requis :
    - Poste (Titre du job)
    - Entreprise (Nom de la boite, ou "Non spécifié")
    - Lieu (Ville/Pays, ou "Non spécifié")
    - Missions (Copie la partie description des taches)
    - Profil_Recherche (Copie la partie compétences/profil)

    Si tu ne trouves pas une info, mets "Non spécifié".
    Ne rajoute aucun texte avant ou après le JSON.
    
    Format de sortie :
    {{
        "Poste": "...",
        "Entreprise": "...",
        "Lieu": "...",
        "Missions": "...",
        "Profil_Recherche": "..."
    }}

    ANNONCE :
    {raw_text[:3000]} 
    (Texte tronqué à 3000 chars pour performance)
    """

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

    generated_ids = model.generate(
        **model_inputs,
        max_new_tokens=500,
        temperature=0.1,
        do_sample=False 
    )
    
    generated_ids = [
        output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
    ]
    response_text = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

    # 3. Parsing JSON
    try:
        # Simple cleanup if model chats too much
        json_str = response_text.strip()
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0]
        elif "{" in json_str and "}" in json_str:
            start = json_str.find("{")
            end = json_str.rfind("}") + 1
            json_str = json_str[start:end]
            
        data = json.loads(json_str)

        # CLEANUP: Remove newlines from all fields to match CSV expectations
        def clean_val(v):
            if isinstance(v, str):
                return v.replace('\n', ' ').replace('\r', ' ').strip()
            return v

        for k, v in data.items():
            data[k] = clean_val(v)

        data['Lien'] = "Texte Brut (Manuel)"
        
        # Create DataFrame
        df = pd.DataFrame([data])
        
        # Save to CSV (This REPLACES jobs_raw.csv as per Step 1 behavior)
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
            
        output_path = os.path.join(DATA_DIR, "jobs_raw.csv")
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        
        if progress_callback:
            progress_callback(f"✅ Analyse réussie : {data.get('Poste', 'Job')} chez {data.get('Entreprise', 'N/A')}")

    except Exception as e:
        if progress_callback:
            progress_callback(f"❌ Erreur parsing JSON sortie IA : {e}\nRaw output: {response_text[:100]}...")
        return None

    # Cleanup
    del model
    del tokenizer
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    gc.collect()

    return output_path
