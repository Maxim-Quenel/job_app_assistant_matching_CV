from flask import Flask, render_template, request, jsonify, send_from_directory
import threading
import os
import pandas as pd
import time

# Services
from services.scraper import scrape_jobs
from services.raw_job_parser import parse_raw_job_text # IMPORT ADDED
from services.job_rewriter import rewrite_jobs
from services.cv_converter import convert_cv_to_txt
from services.cv_rewriter import rewrite_cv
from services.matcher import calculate_matches
from services.cross_encoder_matcher import calculate_cross_matches # IMPORT ADDED
from services.explain import explain_matches # IMPORT ADDED
from utils.logger import logger

app = Flask(__name__)
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

# Ensure data dir exists
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

@app.route('/')
def index():
    logger.reset_state()
    return render_template('index.html')

@app.route('/api/logs')
def get_logs():
    return jsonify(logger.get_logs())

@app.route('/api/files/<filename>')
def download_file(filename):
    return send_from_directory(DATA_DIR, filename)

def run_task(task_id, task_func, *args, **kwargs):
    """Helper to run tasks in a separate thread"""
    def wrapper():
        try:
            logger.start_task(task_id)
            task_func(*args, progress_callback=logger.log, **kwargs)
            logger.finish_task()
        except Exception as e:
            logger.error_task(str(e))
    
    thread = threading.Thread(target=wrapper)
    thread.start()

# --- PREVIEW ENDPOINTS ---
@app.route('/api/preview/step1')
def preview_step1():
    try:
        df = pd.read_csv(os.path.join(DATA_DIR, "jobs_raw.csv"))
        return jsonify(df.head(3).to_dict(orient='records'))
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/preview/step2')
def preview_step2():
    try:
        df = pd.read_csv(os.path.join(DATA_DIR, "jobs_rewritten.csv"))
        # Show specific columns
        cols = ['Poste', 'Entreprise', 'Resume_IA']
        return jsonify(df[cols].fillna("").to_dict(orient='records'))
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/preview/step3')
def preview_step3():
    try:
        with open(os.path.join(DATA_DIR, "cv_converted.txt"), 'r', encoding='utf-8') as f:
            content = f.read() # Full content
        return jsonify({"content": content})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/preview/step4')
def preview_step4():
    try:
        with open(os.path.join(DATA_DIR, "cv_synthesized.txt"), 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({"content": content})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/preview/step5')
def preview_step5():
    try:
        df = pd.read_csv(os.path.join(DATA_DIR, "final_matches.csv"))
        # Return top 5 matches with more details
        cols = ['Poste', 'Entreprise', 'match_score', 'Lien', 'Resume_IA', 'Missions']
        # Filter cols that actually exist
        existing_cols = [c for c in cols if c in df.columns]
        result = df[existing_cols].head(5).fillna("").to_dict(orient='records')
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/preview/step6')
def preview_step6():
    try:
        df = pd.read_csv(os.path.join(DATA_DIR, "final_matches_cross.csv"))
        # Return top 5 matches with more details
        cols = ['Poste', 'Entreprise', 'match_score', 'Lien', 'Resume_IA', 'Missions']
        # Filter cols that actually exist
        existing_cols = [c for c in cols if c in df.columns]
        result = df[existing_cols].head(5).fillna("").to_dict(orient='records')
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/preview/step7')
def preview_step7():
    try:
        df = pd.read_csv(os.path.join(DATA_DIR, "explained_matches.csv"))
        # Return top 5 matches with explanations
        cols = ['Poste', 'Entreprise', 'match_score', 'Explanation']
        # Filter cols that actually exist
        existing_cols = [c for c in cols if c in df.columns]
        result = df[existing_cols].fillna("").to_dict(orient='records')
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})


# --- STEP 1: SCRAPING / RAW INPUT ---
@app.route('/api/step1', methods=['POST'])
def step1_scrape():
    data = request.json
    mode = data.get('mode', 'scrape') # 'scrape' or 'text'
    
    if mode == 'text':
        raw_text = data.get('text', '')
        run_task('step1', parse_raw_job_text, raw_text=raw_text)
    else:
        keyword = data.get('keyword', 'Data Analyst')
        num_jobs = int(data.get('num_jobs', 5))
        run_task('step1', scrape_jobs, keyword=keyword, num_jobs=num_jobs)
        
    return jsonify({"status": "started"})

# --- STEP 2: JOB REWRITE ---
@app.route('/api/step2', methods=['POST'])
def step2_rewrite_jobs():
    run_task('step2', rewrite_jobs)
    return jsonify({"status": "started"})

# --- STEP 3: CV CONVERT ---
@app.route('/api/step3/upload', methods=['POST'])
def upload_cv():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    filepath = os.path.join(DATA_DIR, file.filename)
    file.save(filepath)
    return jsonify({"status": "ok", "filename": file.filename})

@app.route('/api/step3', methods=['POST'])
def step3_convert_cv():
    data = request.json
    filename = data.get('filename')
    
    pdf_path = os.path.join(DATA_DIR, filename)
    run_task('step3', convert_cv_to_txt, pdf_path=pdf_path)
    return jsonify({"status": "started"})

# --- STEP 4: CV REWRITE ---
@app.route('/api/step4', methods=['POST'])
def step4_rewrite_cv():
    run_task('step4', rewrite_cv)
    return jsonify({"status": "started"})

# --- STEP 5: MATCHING ---
@app.route('/api/step5', methods=['POST'])
def step5_matching():
    run_task('step5', calculate_matches)
    return jsonify({"status": "started"})

# --- STEP 6: CROSS MATCHING ---
@app.route('/api/step6', methods=['POST'])
def step6_cross_matching():
    run_task('step6', calculate_cross_matches)
    return jsonify({"status": "started"})

# --- STEP 7: EXPLAIN MATCHES ---
@app.route('/api/step7', methods=['POST'])
def step7_explain_matches():
    run_task('step7', explain_matches)
    return jsonify({"status": "started"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
