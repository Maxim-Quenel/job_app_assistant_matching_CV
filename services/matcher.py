import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import os
import gc
import torch

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')

def calculate_matches(cv_txt_path=None, jobs_csv_path=None, progress_callback=None):
    """
    Calculates matching score between CV and Jobs.
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
    if progress_callback:
        progress_callback("Chargement du modèle 'BAAI/bge-m3'...")
    
    model = SentenceTransformer('BAAI/bge-m3')

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

    # 3. Vectorization
    if progress_callback:
        progress_callback(f"Vectorisation du CV et des {len(df_jobs)} offres...")

    df_jobs['text_complet'] = (
        df_jobs['Poste'].astype(str) + " " + 
        df_jobs['Entreprise'].astype(str) + " " + 
        df_jobs['Resume_IA'].astype(str)
    )

    cv_vector = model.encode([cv_text])
    job_vectors = model.encode(df_jobs['text_complet'].tolist())

    # 4. Similarity
    scores = cosine_similarity(cv_vector, job_vectors)[0]
    df_jobs['match_score'] = scores * 100
    
    df_result = df_jobs.sort_values(by='match_score', ascending=False)
    
    output_path = os.path.join(DATA_DIR, 'final_matches.csv')
    df_result.to_csv(output_path, index=False)
    
    if progress_callback:
        progress_callback(f"✅ Matching terminé. Top score : {df_result.iloc[0]['match_score']:.2f}%")

    # Cleanup
    del model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    gc.collect()

    return output_path
