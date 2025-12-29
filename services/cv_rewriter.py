import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import os
import gc

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')

def rewrite_cv(cv_txt_path=None, progress_callback=None):
    """
    Rewrites CV using Qwen model.
    """
    if cv_txt_path is None:
        cv_txt_path = os.path.join(DATA_DIR, "cv_converted.txt")
        
    if not os.path.exists(cv_txt_path):
        if progress_callback:
            progress_callback("❌ Erreur : Fichier cv_converted.txt non trouvé. Veuillez lancer l'étape 3.")
        return None

    # 1. Read File
    with open(cv_txt_path, 'r', encoding='utf-8') as f:
        cv_content = f.read()

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

    # 3. Prompt Optimisé pour Qwen 2.5 1.5B

    system_prompt = """Tu es un assistant de synthèse RH.
    Ta fonction est de transformer les informations professionnelles d'un CV en une fiche de compétences standardisée.
    Tu dois reformuler le contenu pour qu'il soit totalement neutre et générique.
    Remplace systématiquement l'identité du candidat par le terme : "Candidat".
    Concentre-toi uniquement sur les savoir-faire, les diplômes et l'expérience métier."""

    # ON INVERSE : Le CV est maintenant tout en haut
    user_prompt = f"""
    DOCUMENT À ANALYSER :
    ---
    {cv_content}
    ---

    INSTRUCTIONS :
    A partir du texte ci-dessus, extrais et classe les informations professionnelles.
    Remplis STRICTEMENT le modèle ci-dessous.
    Ne répète pas le texte original. Arrête-toi après la section 5.

    MODELE À REMPLIR :

    ### 1. Synthèse du Profil
    **Intitulé du poste** : [Indiquer le métier principal ici]
    **Resumé** : Candidat expérimenté dans le domaine de [Indiquer le secteur].

    ### 2. Compétences Techniques (Hard Skills)
    [Lister les logiciels, outils et techniques métier]

    ### 3. Qualités Professionnelles (Soft Skills)
    [Lister les qualités humaines et relationnelles]

    ### 4. Analyse de l'Expérience
    **Niveau** : [Junior / Confirmé / Senior]
    **Secteurs dominants** : [Indiquer les industries]
    **Atouts clés** : [Lister les points forts professionnels]

    ### 5. Formation Académique
    [Lister uniquement les diplômes et certificats obtenus]
    """

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

    if progress_callback:
        progress_callback("Génération de la synthèse CV...")

    generated_ids = model.generate(
        **model_inputs,
        max_new_tokens=1000,
        temperature=0.2,
        top_p=0.9,
        repetition_penalty=1.2,
        do_sample=True
    )

    generated_ids = [
        output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
    ]
    full_response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

    output_path = os.path.join(DATA_DIR, "cv_synthesized.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_response)

    if progress_callback:
        progress_callback("✅ Synthèse CV terminée.")

    # Cleanup
    del model
    del tokenizer
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    gc.collect()

    return output_path
