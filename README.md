# Rapport d'Analyse du Projet : Job Application Assistant

[cite_start]**Auteurs :** Maxim Quénel, Pierre Louis Brun, Mame Alé Seye, Denis Bereziuc [cite: 2]
[cite_start]**Date :** 28 décembre 2025 (Mis à jour) [cite: 3]

**Liens du projet :**
* [cite_start][Dépôt GitHub](https://github.com/Maxim-Quenel/job_app_assistant_matching_CV) [cite: 4]
* [cite_start][Vidéo de démonstration](https://youtu.be/kI_qEuUWzUo?si=bX4tef1I_LSxfEUj) [cite: 4]

---

## Résumé
[cite_start]Ce document présente une analyse détaillée du projet d'assistant de candidature automatisé, couvrant son contexte, son architecture, ses choix techniques, le traitement des données et les perspectives d'évolution[cite: 6].

---

## 1. Contexte du Projet
[cite_start]Le projet **Job Application Assistant** est une application web locale conçue pour automatiser et optimiser le processus de recherche d'emploi[cite: 13]. [cite_start]Il vise à réduire la charge cognitive et temporelle liée à la personnalisation des candidatures en[cite: 14]:
* [cite_start]Récupérant automatiquement des offres d'emploi ciblées[cite: 15].
* [cite_start]Analysant et résumant ces offres pour en extraire les points clés[cite: 16].
* [cite_start]Restructurant le CV du candidat pour l'anonymiser et le standardiser[cite: 17].
* [cite_start]Fournissant une justification textuelle intelligible pour chaque correspondance et calculant un score de pertinence pour prioriser les meilleures opportunités[cite: 18].

## 2. Architecture Technique
[cite_start]L'application repose sur une architecture monolithique modulaire, orchestrée par un serveur web léger[cite: 20].

### 2.1 Composants Principaux
* **Backend (Serveur) :** Développé en Python avec le framework Flask. [cite_start]Il expose des endpoints API (`/api/step1` à `/api/step7`) pour déclencher les différentes étapes du pipeline[cite: 22].
* [cite_start]**Frontend (Interface) :** Pages HTML servies par Flask (`render_template`), interagissant avec l'API via JavaScript pour lancer les tâches et afficher la progression[cite: 23].
* [cite_start]**Task Management :** Utilisation du module `threading` natif de Python pour exécuter les tâches longues (IA, scraping) en arrière-plan sans bloquer l'interface utilisateur[cite: 24].
* **Persistance des Données :** Système de fichiers simple (CSV et TXT) stockés dans un dossier local `data/`. [cite_start]L'absence de base de données relationnelle complexe simplifie le déploiement et le débogage[cite: 25, 26].

### 2.2 Flux de Contrôle
[cite_start]Le flux est séquentiel mais découpé en étapes indépendantes, permettant à l'utilisateur de valider chaque phase intermédiaire[cite: 28]:
[cite_start]`Scraping` → `Job Rewrite` → `CV Convert` → `CV Rewrite` → `Matching` → `Explanation`[cite: 29].

## 3. Choix de Conception
* [cite_start]**Approche "Local-First" et Confidentialité :** Le choix d'utiliser des modèles d'IA exécutés localement via la librairie `transformers` (plutôt que des API cloud payantes) garantit la confidentialité des données sensibles (CVs) et l'indépendance vis-à-vis des coûts récurrents[cite: 31].
* **Modularité des Services :** Chaque fonction métier est isolée dans un module dédié (ex: `services/scraper.py`, `services/job_rewriter.py`). [cite_start]Cela facilite la maintenance et les tests unitaires[cite: 32, 33].
* **État basé sur des fichiers :** L'utilisation de fichiers tels que `jobs_raw.csv` ou `cv_synthesized.txt` permet une transparence totale. [cite_start]L'utilisateur peut ouvrir ces fichiers pour vérifier ou corriger les données manuellement[cite: 35, 36].

## 4. Traitement des Données (Data Pipeline)
[cite_start]Le pipeline de données transforme des informations non structurées en scores exploitables[cite: 38]:

* [cite_start]**Ingestion (Étape 1) :** Les offres sont scrapées ou saisies par texte brut et stockées dans `jobs_raw.csv`[cite: 40, 41].
* **Normalisation (Étape 2 & 4) :**
    * [cite_start]*Offres :* Le LLM nettoie et structure les descriptions dans une nouvelle colonne "Resume_IA"[cite: 43].
    * [cite_start]*CV :* Conversion PDF vers TXT, suivie d'une réécriture par LLM pour standardiser le format et anonymiser les données[cite: 44].
* **Matching (Étape 5 & 6) :** Construction de paires (Texte du CV, Texte de l'Offre). [cite_start]Les offres "enrichies" combinent le poste, l'entreprise et le résumé IA pour donner un contexte maximal au modèle [cite: 46-48].
* **Explication & Justification (Étape 7) :**
    * [cite_start]Récupération du CV synthétisé et des offres enrichies[cite: 50].
    * [cite_start]Analyse sémantique croisée par le modèle (Qwen)[cite: 51].
    * [cite_start]Génération d'une critique structurée et classification explicite ("Match Fort", "Partiel" ou "Pas de Match")[cite: 52].
    * [cite_start]Consolidation dans un fichier CSV incluant une colonne "Explanation"[cite: 53].

## 5. Choix du Fournisseur LLM & Modèles
[cite_start]Le projet utilise des modèles Open Source performants exécutés via Hugging Face Transformers[cite: 55].

### 5.1 Modèle Génératif (Mise en forme)
* [cite_start]**Modèle :** `Qwen/Qwen2.5-1.5B-Instruct`[cite: 58].
* **Justification :** C'est un "Small Language Model" (SLM) de 1.5 milliard de paramètres. [cite_start]Il est suffisamment léger pour tourner sur des GPU grand public tout en offrant une excellente capacité de suivi d'instructions[cite: 59, 60].
* [cite_start]**Utilisation :** Réécriture des CVs/Offres et génération des explications avec une température faible (0.1/0.2)[cite: 61].

### 5.2 Modèles de Matching (Scoring)
[cite_start]Le projet implémente une stratégie de matching à deux niveaux[cite: 63]:

#### 5.2.1 Approche Classique (Bi-Encoder)
* [cite_start]**Modèle :** `BAAI/bge-m3`[cite: 65].
* **Fonctionnement :** Conversion indépendante du CV et des offres en vecteurs. [cite_start]Similarité calculée par cosinus[cite: 67].
* [cite_start]**Rôle :** Premier filtre rapide (Étape 5)[cite: 68].

#### 5.2.2 Approche Avancée (Cross-Encoder/Reranking)
* [cite_start]**Modèle :** `BAAI/bge-reranker-v2-m3`[cite: 70].
* [cite_start]**Fonctionnement :** Le modèle analyse le CV et l'offre ensemble pour estimer une similarité sémantique fine[cite: 72].
* [cite_start]**Rôle :** Affinement final plus précis (Étape 6), produisant un score de pertinence entre 0 et 100%[cite: 73].

## 6. Évaluation Quantitative
[cite_start]Cette section détaille la validation technique du moteur de matching sur un échantillon de validation ($N=20$) issu du dataset `Oxnbk/resume-ats-score-v1-en`[cite: 75].

### 6.1 Protocole de Test
[cite_start]Le pipeline d'évaluation reproduit strictement l'architecture de l'application : Denoising (Qwen), Scoring (BAAI Reranker) et comparaison avec la vérité terrain (`ats_score`) [cite: 77-80].

### 6.2 Résultats Obtenus
[cite_start]L'évaluation sur 15 échantillons a produit les métriques suivantes (Seuil de décision fixé à 0.55)[cite: 83]:

| Métrique | Valeur | Interprétation |
| :--- | :--- | :--- |
| **Précision** | 0.667 | [cite_start]Lorsque le modèle prédit un match, il a raison dans 67% des cas[cite: 84]. |
| **Rappel (Recall)** | 0.222 | Le modèle ne détecte que 22% des bons candidats. [cite_start]Il est trop sélectif[cite: 84]. |
| **F1-Score** | 0.333 | [cite_start]Score global moyen, pénalisé par le faible rappel[cite: 84]. |
| **MAP** | 0.640 | [cite_start]Point fort: Malgré des scores absolus bas, le classement relatif est cohérent[cite: 84]. |
| **Pearson** | 0.271 | [cite_start]Corrélation linéaire faible[cite: 84]. |
| **Spearman** | 0.235 | [cite_start]Corrélation de rang faible[cite: 84]. |

### 6.3 Analyse Critique des Données
1.  **Zone Grise du Modèle :** La majorité des scores prédits se situe entre 0.50 et 0.52. [cite_start]Le nettoyage par le LLM standardise peut-être trop les textes, supprimant des nuances spécifiques [cite: 89-91].
2.  **Divergence de Logique ATS :** Il existe une divergence entre la logique de scoring du dataset (mots-clés exacts) et notre approche (sémantique). [cite_start]Par exemple, le modèle prédit un match (0.616) là où l'ATS le rejette (0.247), suggérant la détection de compétences transférables [cite: 93-95].

### 6.4 Conclusion de l'Évaluation
[cite_start]Le système actuel présente une bonne Précision (il ne propose pas n'importe quoi) mais un mauvais Rappel (il rate beaucoup d'opportunités)[cite: 97].

## 7. Améliorations Futures Recommandées

### 7.1 Technique
* [cite_start]**File de Tâches Robuste :** Remplacer `threading` par une solution comme Celery ou RQ (avec Redis)[cite: 102].
* [cite_start]**Base de Données :** Migrer des fichiers CSV vers SQLite pour permettre des requêtes complexes[cite: 103].
* [cite_start]**Optimisation Inférence :** Implémenter la quantification (4-bit via bitsandbytes) pour accélérer le chargement et réduire la consommation VRAM[cite: 104].

### 7.2 Fonctionnel
* [cite_start]**Feedback Loop :** Ajouter un système de notation ("Pouce haut/bas") pour affiner les futurs modèles[cite: 106].
* [cite_start]**Génération de Lettre de Motivation :** Utiliser Qwen pour rédiger une lettre personnalisée basée sur le CV et l'offre[cite: 107].
* [cite_start]**Interface de Filtrage :** Permettre le filtrage par score minimum ou mots-clés[cite: 108].

### 7.3 Qualité du Code
* [cite_start]**Gestion des Erreurs :** Renforcer les blocs `try/except` autour des appels réseaux[cite: 110].
* [cite_start]**Configuration :** Centraliser les constantes dans un fichier `config.py` ou des variables d'environnement[cite: 111].

---

# Documentation Technique : Architecture du Projet

## 8. Objectif
Le projet est une application web Flask conçue pour automatiser le processus de recherche d'emploi. Elle orchestre un flux complet allant de la récupération des offres à l'analyse de pertinence via l'Intelligence Artificielle (LLM). [cite_start]L'interface propose un parcours utilisateur en 7 étapes distinctes [cite: 115-117].

## 9. Structure du Dépôt
[cite_start]L'organisation des fichiers suit une logique modulaire[cite: 119]:
* `app.py`: Point d'entrée de l'application Flask. [cite_start]Gère les routes API et l'orchestration[cite: 120].
* [cite_start]`services/`: Contient toute la logique métier (scraping, parsing, réécriture LLM, matching)[cite: 121].
* [cite_start]`utils/`: Utilitaires transverses, notamment le logger applicatif[cite: 122].
* [cite_start]`templates/index.html`: Interface web unique (6 cartes interactives + logs)[cite: 123].
* [cite_start]`static/`: Ressources frontend (CSS/JS) gérant les interactions et le polling[cite: 124].
* [cite_start]`data/`: Dossier de stockage pour les fichiers intermédiaires et résultats[cite: 125].
* [cite_start]`msedgedriver.exe`: Driver Selenium pour le navigateur Edge[cite: 126].

## 10. Flux Fonctionnel (Pipeline)
[cite_start]Le traitement des données suit un pipeline séquentiel[cite: 128]:

1.  **Étape 1: Collecte des Offres**
    * Méthodes : Scraping (HelloWork) via `services/scraper.py` ou Import manuel via `services/raw_job_parser.py`.
    * [cite_start]Sortie : `data/jobs_raw.csv`[cite: 130, 131].
2.  **Étape 2: Réécriture des Offres (Enrichissement)**
    * Traitement : Résumé et structuration via Qwen (`services/job_rewriter.py`).
    * [cite_start]Sortie : `data/jobs_rewritten.csv` [cite: 133-135].
3.  **Étape 3: Conversion du CV**
    * Traitement : Extraction PDF via pdfplumber (`services/cv_converter.py`).
    * [cite_start]Sortie : `data/cv_converted.txt` [cite: 137-139].
4.  **Étape 4: Synthèse du CV**
    * Traitement : Réécriture et normalisation via LLM (`services/cv_rewriter.py`).
    * [cite_start]Sortie : `data/cv_synthesized.txt`[cite: 140, 141].
5.  **Étape 5: Matching Sémantique**
    * Traitement : Similarité cosinus sur embeddings BAAI/bge-m3 (`services/matcher.py`).
    * [cite_start]Sortie : `data/final_matches.csv` [cite: 142-145].
6.  **Étape 6: Cross-Matching (Reranking)**
    * Traitement : Affinement via Cross-Encoder BAAI/bge-reranker (`services/cross_encoder_matcher.py`).
    * [cite_start]Sortie : `data/final_matches_cross.csv` [cite: 146-148].
7.  **Étape 7: Explication des Matchs**
    * Traitement : Analyse sémantique et narrative via Qwen (`services/explain.py`).
    * [cite_start]Sortie : `data/explained_matches.csv` [cite: 149-152].

## 11. Backend (Flask)
[cite_start]Le fichier `app.py` centralise la logique serveur[cite: 154].

### 11.1 Routes Principales
* [cite_start]`GET /`: Chargement de l'application[cite: 156].
* [cite_start]`GET /api/logs`: Récupération des logs pour l'UI[cite: 157].
* [cite_start]`GET /api/preview/step1..step7`: Affichage d'échantillons de données[cite: 158].
* [cite_start]`GET /api/files/<filename>`: Téléchargement des fichiers[cite: 159].
* [cite_start]`POST /api/step1` à `/api/step7`: Déclencheurs des traitements[cite: 159].
* [cite_start]`POST /api/step3/upload`: Upload du CV PDF[cite: 160].

### 11.2 Orchestration
* [cite_start]**Run Task :** Exécute chaque étape dans un thread séparé pour éviter de bloquer le serveur[cite: 162].
* [cite_start]**Logger :** Centralise le statut des opérations et alimente l'interface en temps réel[cite: 163].

## 12. Services (Logique Métier)
[cite_start]Responsabilité unique par script dans `services/`[cite: 166]:
* `scraper.py`: Pilotage Selenium (Edge).
* `raw_job_parser.py`: Conversion texte brut en JSON via Qwen.
* `job_rewriter.py`: Résumés structurés d'offres.
* `cv_converter.py`: Extraction brute PDF.
* `cv_rewriter.py`: Synthèse standardisée du CV.
* `matcher.py`: Matching rapide (Bi-Encoder).
* `cross_encoder_matcher.py`: Matching de précision (Cross-Encoder).
* [cite_start]`explain.py`: Verdict et explication textuelle [cite: 167-172].

## 13. Frontend
[cite_start]Géré par `templates/index.html` et `static/js/main.js`[cite: 174].
* [cite_start]**Structure :** 7 cartes (étapes du pipeline) + terminal de logs[cite: 175].
* [cite_start]**Mécanique :** Polling sur `/api/logs` toutes les secondes[cite: 176].
* [cite_start]**Visualisation :** Prévisualisation des résultats intermédiaires sans quitter l'interface[cite: 177].

## 14. Données et Artefacts
[cite_start]Stockés localement dans `data/`[cite: 180]:
* `jobs_raw.csv` (Brut)
* `jobs_rewritten.csv` (Enrichi)
* `cv_converted.txt` (Extraction CV)
* `cv_synthesized.txt` (Profil structuré)
* `final_matches.csv` (Filtre sémantique)
* `final_matches_cross.csv` (Classement final)
* [cite_start]`explained_matches.csv` (Résultat final expliqué) [cite: 181-187].

## 15. Dépendances Clés
* **Backend :** Flask
* **Données :** Pandas
* **Scraping :** Selenium + Edge Driver
* **PDF :** pdfplumber
* [cite_start]**IA & NLP :** Transformers, Torch, Sentence-Transformers, Scikit-learn [cite: 190-194].
