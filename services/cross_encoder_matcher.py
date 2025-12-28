import pandas as pd
from sentence_transformers import CrossEncoder
import os
import gc
import torch

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')

def calculate_cross_matches(cv_txt_path=None, jobs_csv_path=None, progress_callback=None):
    """
    Calculates matching score between CV and Jobs using a Cross Encoder.
    """
    if cv_txt_path is None:
        cv_txt_path = os.path.join(DATA_DIR, "cv_synthesized.txt")
    if jobs_csv_path is None:
        jobs_csv_path = os.path.join(DATA_DIR, "jobs_rewritten.csv")

    if not os.path.exists(cv_txt_path):
        if progress_callback:
            progress_callback("❌ Erreur : Synthèse CV manquante. Veuillez lancer l'étape 4.")
        return None
    
    if not os.path.exists(jobs_csv_path):
        if progress_callback:
            progress_callback("❌ Erreur : Offres réécrites manquantes. Veuillez lancer l'étape 2.")
        return None

    # 1. Load Model
    model_name = "BAAI/bge-reranker-v2-m3"
    if progress_callback:
        progress_callback(f"Chargement du modèle Cross Encoder '{model_name}'...")
    
    try:
        # CrossEncoder handles the classification/scoring directly
        model = CrossEncoder(model_name)
    except Exception as e:
        if progress_callback:
            progress_callback(f"❌ Erreur chargement modèle : {e}")
        return None

    # 2. Read Data
    try:
        with open(cv_txt_path, 'r', encoding='utf-8') as f:
            cv_text = f.read()
        
        df_jobs = pd.read_csv(jobs_csv_path)
        df_jobs = df_jobs.fillna('') 
    except Exception as e:
        if progress_callback:
            progress_callback(f"❌ Erreur lecture fichiers : {e}")
        return None

    # 3. Prepare Pairs
    if progress_callback:
        progress_callback(f"Préparation des paires pour {len(df_jobs)} offres...")

    df_jobs['text_complet'] = (
        df_jobs['Poste'].astype(str) + " " + 
        df_jobs['Entreprise'].astype(str) + " " + 
        df_jobs['Resume_IA'].astype(str)
    )

    # Pairs format: [[Query, Doc1], [Query, Doc2], ...]
    pairs = [[cv_text, job_text] for job_text in df_jobs['text_complet'].tolist()]

    # 4. Predict
    if progress_callback:
        progress_callback("Calcul des scores (Inférence)...")

    # Scores are logits usually (unbounded), or 0-1 if sigmoid is applied.
    # BGE Reranker output is usually raw logits. We can accept them as is for ranking or normalize.
    # For UI display as %, we might want to normalize, but sigmoid is good for probability.
    scores = model.predict(pairs)

    # Simple normalization for display: sigmod if not applied, or just rank.
    # BGE-M3 often outputs logits. Let's apply a sigmoid manually to get 0-1 range for "percentage".
    # Or just keep raw scores for sorting.
    # Let's use sigmoid to get a nice 0-100 score.
    
    import numpy as np
    def sigmoid(x):
        return 1 / (1 + np.exp(-x))
    
    # Apply sigmoid to logic
    probs = sigmoid(scores)
    
    df_jobs['match_score'] = probs * 100
    
    df_result = df_jobs.sort_values(by='match_score', ascending=False)
    
    output_path = os.path.join(DATA_DIR, 'final_matches_cross.csv')
    df_result.to_csv(output_path, index=False)
    
    if progress_callback:
        progress_callback(f"✅ Cross-Matching terminé. Top score : {df_result.iloc[0]['match_score']:.2f}%")

    # Cleanup
    del model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    gc.collect()

    return output_path
