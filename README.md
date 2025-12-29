# Documentation du Projet : Job Application Assistant
* [cite_start][Vidéo de démonstration](https://youtu.be/kI_qEuUWzUo?si=bX4tef1I_LSxfEUj)

## 1. Contexte du Projet

Le projet **Job Application Assistant** est une application web locale conçue pour automatiser et optimiser le processus de recherche d’emploi. Il vise à réduire la charge cognitive et temporelle liée à la personnalisation des candidatures en :

* Récupérant automatiquement des offres d’emploi ciblées.
* Analysant et résumant ces offres pour en extraire les points clés.
* Restructurant le CV du candidat pour l’anonymiser et le standardiser.
* Fournissant une justification textuelle intelligible pour chaque correspondance.
* Calculant un score de pertinence (*matching*) entre le CV et chaque offre pour prioriser les meilleures opportunités.

---

## 2. Architecture Technique

L’application repose sur une architecture monolithique modulaire, orchestrée par un serveur web léger.

### 2.1 Composants Principaux

* **Backend (Serveur) :** Développé en **Python** avec le framework **Flask**. Il expose des endpoints API (de `/api/step1` à `/api/step7`) pour déclencher les différentes étapes du pipeline.
* **Frontend (Interface) :** Pages HTML servies par Flask (`render_template`), interagissant avec l’API via JavaScript pour lancer les tâches et afficher la progression.
* **Task Management :** Utilisation du module `threading` natif de Python pour exécuter les tâches longues (IA, scraping) en arrière-plan sans bloquer l’interface utilisateur.
* **Persistance des Données :** Système de fichiers simple (CSV et TXT) stockés dans un dossier local `data/`. L’absence de base de données relationnelle complexe simplifie le déploiement et le débogage.

### 2.2 Flux de Contrôle

Le flux est séquentiel mais découpé en étapes indépendantes, permettant à l’utilisateur de valider chaque phase intermédiaire :

> **Scraping → Job Rewrite → CV Convert → CV Rewrite → Matching → Explanation**

---

## 3. Choix de Conception

* **Approche "Local-First" et Confidentialité :** Le choix d’utiliser des modèles d’IA exécutés localement via la librairie `transformers` (plutôt que des API cloud payantes) garantit la confidentialité des données sensibles (CVs) et l’indépendance vis-à-vis des coûts récurrents.
* **Modularité des Services :** Chaque fonction métier est isolée dans un module dédié (ex : `services/scraper.py`, `services/job_rewriter.py`). Cela facilite la maintenance, les tests unitaires et le remplacement potentiel d’un composant.
* **État basé sur des fichiers :** L’utilisation de fichiers tels que `jobs_raw.csv`, `jobs_rewritten.csv` ou `cv_synthesized.txt` permet une transparence totale. L’utilisateur peut ouvrir ces fichiers pour vérifier ou corriger les données manuellement.

---

## 4. Traitement des Données (Data Pipeline)

Le pipeline de données transforme des informations non structurées en scores exploitables :

### Ingestion (Étape 1)
* Les offres sont scrapées ou saisies par texte brut.
* Stockage initial dans le fichier `jobs_raw.csv`.

### Normalisation (Étape 2 & 4)
* **Offres :** Le LLM nettoie et structure les descriptions (compétences, missions, infos clés) dans une nouvelle colonne `Resume_IA`.
* **CV :** Conversion PDF vers TXT, suivie d’une réécriture par LLM pour standardiser le format et anonymiser les données personnelles.

### Matching (Étape 5 & 6)
* Construction de paires (Texte du CV, Texte de l’Offre).
* Les offres "enrichies" combinent le poste, l’entreprise et le résumé IA pour donner un contexte maximal au modèle de matching.

### Explication & Justification (Étape 7)
* **Entrées :** Récupération du CV synthétisé et des offres d’emploi enrichies.
* **Analyse par le LLM :** Le modèle (Qwen) effectue une évaluation sémantique croisée de la paire Candidat/Offre.
* **Génération du verdict :** Production d’une critique structurée en trois points clés, conclue par une classification explicite ("Match Fort", "Partiel" ou "Pas de Match").
* **Livrable final :** Consolidation des données dans un fichier CSV incluant une colonne `Explanation`.

---

## 5. Choix du Fournisseur LLM & Modèles

Le projet utilise des modèles Open Source performants exécutés via Hugging Face Transformers.

### 5.1 Modèle Génératif (Mise en forme)
* **Modèle :** `Qwen/Qwen2.5-1.5B-Instruct`
* **Justification :** C'est un "Small Language Model" (SLM) très performant pour sa taille (1.5 milliard de paramètres). Il est suffisamment léger pour tourner sur des GPU grand public tout en offrant une excellente capacité de suivi d’instructions.
* **Utilisation :** Réécriture des CVs, des offres et génération des explications avec une température faible (0.1/0.2).

### 5.2 Modèles de Matching (Scoring)
Le projet implémente une stratégie de matching à deux niveaux :

#### 5.2.1 Approche Classique (Bi-Encoder)
* **Modèle :** `BAAI/bge-m3` (Sentence Transformer)
* **Fonctionnement :** Conversion indépendante du CV et des offres en vecteurs. Similarité calculée par cosinus.
* **Rôle :** Premier filtre rapide (Étape 5).

#### 5.2.2 Approche Avancée (Cross-Encoder/Reranking)
* **Modèle :** `BAAI/bge-reranker-v2-m3` (Cross-Encoder)
* **Fonctionnement :** Analyse conjointe du CV et de l’offre pour estimer une similarité sémantique fine.
* **Rôle :** Affinement final plus précis (Étape 6), produisant un score de 0 à 100%.

---

## 6. Évaluation Quantitative

Validation technique basée sur un échantillon de validation (N = 20) issu du dataset `0xnbk/resume-ats-score-v1-en`.

### 6.1 Protocole de Test
Pipeline reproduisant l'architecture de l'application : Denoising (Qwen) → Scoring (BAAI Cross-Encoder) → Comparaison avec vérité terrain (`ats_score`).

### 6.2 Résultats Obtenus (Seuil 0.55)

| Métrique | Valeur | Interprétation |
| :--- | :--- | :--- |
| **Précision** | 0.667 | Lorsque le modèle prédit un match, il a raison dans 67% des cas. |
| **Rappel** | 0.222 | Le modèle ne détecte que 22% des bons candidats (trop sélectif). |
| **F1-Score** | 0.333 | Score global moyen, pénalisé par le faible rappel. |
| **MAP** | 0.640 | **Point fort :** Le classement relatif est cohérent. |
| **Pearson** | 0.271 | Corrélation linéaire faible. |
| **Spearman** | 0.235 | Corrélation de rang faible. |

### 6.3 Analyse Critique
1.  **Zone Grise :** La majorité des scores prédits se situe entre 0.50 et 0.52 (score neutre). Le nettoyage par le LLM standardise peut-être trop les textes.
2.  **Divergence ATS :** Le modèle détecte parfois une pertinence sémantique (compétences transférables) là où un ATS classique (mots-clés) rejette le candidat.

---

## 7. Améliorations Futures Recommandées

### 7.1 Technique
* **File de Tâches :** Remplacer `threading` par Celery ou RQ (avec Redis).
* **Base de Données :** Migrer vers SQLite pour permettre des requêtes complexes.
* **Optimisation Inférence :** Implémenter la quantification (4-bit via `bitsandbytes`).

### 7.2 Fonctionnel
* **Feedback Loop :** Système de notation utilisateur pour affiner les modèles.
* **Lettre de Motivation :** Génération automatique via Qwen.
* **Filtres :** Filtrage des résultats par score ou mots-clés.

### 7.3 Qualité du Code
* **Gestion des Erreurs :** Renforcer les blocs `try/except`.
* **Configuration :** Centraliser les constantes dans un `config.py`.

---
---

# Documentation Technique : Architecture du Projet

## 8. Objectif
Application web Flask pour automatiser la recherche d’emploi, orchestrant un flux de la récupération des offres à l’analyse de pertinence via IA.

## 9. Structure du Dépôt

* `app.py` : Point d’entrée Flask, gestion des routes et threads.
* `services/` : Logique métier (scraping, parsing, LLM, matching).
* `utils/` : Utilitaires (logger applicatif).
* `templates/index.html` : Interface web unique.
* `static/` : Ressources CSS/JS.
* `data/` : Stockage des fichiers intermédiaires et résultats.
* `msedgedriver.exe` : Driver Selenium pour Edge.

## 10. Flux Fonctionnel (Pipeline)

### Étape 1 : Collecte des Offres
* **Scraping :** `services/scraper.py` (cible : HelloWork).
* **Texte Brut :** `services/raw_job_parser.py`.
* **Sortie :** `data/jobs_raw.csv`.

### Étape 2 : Réécriture des Offres
* **Traitement :** Modèle Qwen via `services/job_rewriter.py`.
* **Sortie :** `data/jobs_rewritten.csv` (ajout colonne `Resume_IA`).

### Étape 3 : Conversion du CV
* **Traitement :** Extraction PDF via `pdfplumber` (`services/cv_converter.py`).
* **Sortie :** `data/cv_converted.txt`.

### Étape 4 : Synthèse du CV
* **Traitement :** Normalisation par LLM (`services/cv_rewriter.py`).
* **Sortie :** `data/cv_synthesized.txt`.

### Étape 5 : Matching Sémantique
* **Traitement :** Similarité cosinus via Bi-Encoder (`services/matcher.py`).
* **Sortie :** `data/final_matches.csv`.

### Étape 6 : Cross-Matching (Reranking)
* **Traitement :** Cross-Encoder pour affinement (`services/cross_encoder_matcher.py`).
* **Sortie :** `data/final_matches_cross.csv`.

### Étape 7 : Explication des Matchs
* **Traitement :** Analyse sémantique par Qwen (`services/explain.py`).
* **Sortie :** `data/explained_matches.csv`.

## 11. Backend (Flask)

### 11.1 Routes Principales
* `GET /` : Application principale.
* `GET /api/logs` : État des tâches et logs.
* `GET /api/preview/step1..7` : Prévisualisation des données.
* `POST /api/step1` à `/api/step7` : Déclencheurs.

### 11.2 Orchestration
* **Threads :** `run_task()` pour éviter le blocage.
* **Logger :** `utils/logger.py` pour le temps réel.

## 12. Services (Logique Métier)
* `scraper.py`, `raw_job_parser.py` : Ingestion.
* `job_rewriter.py`, `cv_rewriter.py` : Traitement LLM.
* `cv_converter.py` : Traitement PDF.
* `matcher.py`, `cross_encoder_matcher.py` : Moteurs de recherche vectorielle.
* `explain.py` : Génération de langage naturel.

## 13. Frontend
* Polling sur `/api/logs` (JS).
* 7 cartes interactives correspondant aux étapes.
* Prévisualisation sans quitter l'interface.

## 14. Données et Artefacts
Tous les fichiers sont dans `data/` pour assurer la traçabilité et le débogage manuel (fichiers CSV et TXT).

## 15. Dépendances Clés
* **Backend :** Flask
* **Data :** Pandas
* **Scraping :** Selenium
* **PDF :** pdfplumber
* **IA :** Transformers, Torch, Scikit-learn
