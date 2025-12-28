# Rapport d'Analyse du Projet : Job Application Assistant

Ce document présente une analyse détaillée du projet d'assistant de candidature automatisé, couvrant son contexte, son architecture, ses choix techniques, le traitement des données et les perspectives d'évolution.

## 1. Contexte du Projet

Le projet **Job Application Assistant** est une application web locale conçue pour automatiser et optimiser le processus de recherche d'emploi. Il vise à réduire la charge cognitive et temporelle liée à la personnalisation des candidatures en :
1.  **Récupérant** automatiquement des offres d'emploi ciblées.
2.  **Analysant et résumant** ces offres pour en extraire les points clés.
3.  **Restructurant** le CV du candidat pour l'anonymiser et le standardiser.
4.  **Calculant un score de pertinence** (matching) entre le CV et chaque offre pour prioriser les meilleures opportunités.

## 2. Architecture Technique

L'application repose sur une architecture monolithique modulaire, orchestrée par un serveur web léger.

### Composants Principaux
*   **Backend (Serveur)** : Développé en **Python** avec le framework **Flask**. Il expose des endpoints API (`/api/step1` à `/api/step6`) pour déclencher les différentes étapes du pipeline.
*   **Frontend (Interface)** : Pages HTML servies par Flask (`render_template`), interagissant avec l'API via JavaScript pour lancer les tâches et afficher la progression.
*   **Task Management** : Utilisation du module `threading` natif de Python pour exécuter les tâches longues (IA, scraping) en arrière-plan sans bloquer l'interface utilisateur.
*   **Persistance des Données** : Système de fichiers simple (CSV et TXT) stockés dans un dossier local `data/`. Pas de base de données relationnelle complexe, ce qui simplifie le déploiement et le débogage.

### Flux de Contrôle
Le flux est séquentiel mais découpé en étapes indépendantes, permettant à l'utilisateur de valider chaque phase intermédiaire :
`Scraping` -> `Job Rewrite` -> `CV Convert` -> `CV Rewrite` -> `Matching`

## 3. Choix de Conception

*   **Approche "Local-First" et Confidentialité** : Le choix d'utiliser des modèles d'IA exécutés localement via la librairie `transformers` (plutôt que des API cloud payantes) garantit la confidentialité des données sensibles (CVs) et l'indépendance vis-à-vis des coûts récurrents.
*   **Modularité des Services** : Chaque fonction métier est isolée dans un module dédié (`services/scraper.py`, `services/job_rewriter.py`, etc.). Cela facilite la maintenance, les tests unitaires et le remplacement potentiel d'un composant (ex: changer de scraper sans casser le reste).
*   **État basé sur des fichiers** : L'utilisation de fichiers `jobs_raw.csv`, `jobs_rewritten.csv`, `cv_synthesized.txt` permet une transparence totale. L'utilisateur peut ouvrir ces fichiers pour vérifier ou corriger les données manuellement si nécessaire.

## 4. Traitement des Données (Data Pipeline)

Le pipeline de données transforme des informations non structurées en scores exploitables :

1.  **Ingestion (Étape 1)** :
    *   Les offres sont scrapées ou saisies par texte brut.
    *   Stockage initial dans `jobs_raw.csv`.
2.  **Normalisation (Étape 2 & 4)** :
    *   **Offres** : Le LLM nettoie et structure les descriptions (compétences, missions, infos clés) dans une nouvelle colonne `Resume_IA`.
    *   **CV** : Conversion PDF -> TXT, puis réécriture par LLM pour standardiser le format et anonymiser les données personnelles.
3.  **Matching (Étape 5 & 6)** :
    *   Construction de paires (Texte du CV, Texte de l'Offre).
    *   Les offres "enrichies" combinent Poste, Entreprise et Résumé IA pour donner un contexte maximal au modèle de matching.

## 5. Choix du Fournisseur LLM & Modèles

Le projet utilise des modèles Open Source performants exécutés via Hugging Face Transformers.

### Modèle Génératif (Mise en forme)
*   **Modèle** : `Qwen/Qwen2.5-1.5B-Instruct`
*   **Justification** : C'est un "Small Language Model" (SLM) très performant pour sa taille (1.5 milliards de paramètres). Il est suffisamment léger pour tourner sur des GPU grand public (ou même CPU avec un peu de lenteur) tout en offrant une excellente capacité de compréhension et de suivi d'instructions pour du résumé de texte.
*   **Utilisation** : Réécriture des CVs et des offres d'emploi. Le code utilise des prompts précis ("Tu es un expert en recrutement...") avec une température faible (0.1/0.2) pour assurer la stabilité des sorties.

### Modèles de Matching (Scoring)

Le projet implémente une **stratégie de matching à deux niveaux** pour comparer l'efficacité des architectures :

#### 1. Approche Classique (Bi-Encoder)
*   **Modèle** : `BAAI/bge-m3`
*   **Type** : Sentence Transformer (Bi-Encoder).
*   **Fonctionnement** : Le CV et les offres sont convertis indépendamment en vecteurs denses (embeddings). La similarité est ensuite calculée par **cosinus**.
*   **Avantage** : Très rapide pour comparer un CV à des milliers d'offres (complexité linéaire).
*   **Utilisation** : C'est le "premier filtre" rapide (Étape 5).

#### 2. Approche Avancée (Cross-Encoder/Reranking)
*   **Modèle** : `BAAI/bge-reranker-v2-m3`
*   **Type** : Cross-Encoder.
*   **Fonctionnement** : Contrairement aux Bi-Encoders, ce modèle prend les deux textes *ensemble* en entrée (CV + Offre) et estime leur similarité sémantique fine via un mécanisme d'attention croisée.
*   **Avantage** : Beaucoup plus précis que le cosinus, car il capte les nuances fines (négation, relation causale).
*   **Score** : Le modèle produit des logits qui sont normalisés (via sigmoïde) pour donner un score de pertinence entre 0 et 100%. Utilisé pour l'affinement final (Étape 6).

## 6. Évaluation

Actuellement, l'évaluation du système est **qualitative et empirique** :
*   Le système affiche les "Top Matches" à l'utilisateur.
*   L'utilisateur juge de la pertinence en consultant les liens ou les résumés.


## 7. Améliorations Futures Recommandées

### Technique
1.  **File de Tâches Robuste** : Remplacer `threading` par une vraie file de tâches comme **Celery** ou **RQ** avec Redis. Cela permettrait de gérer les échecs, les tentatives de relance (retries) et d'éviter de perdre des tâches si le serveur redémarre.
2.  **Base de Données** : Migrer des CSV vers **SQLite**. Cela permettrait des requêtes plus complexes (filtrage par date, par score, par entreprise) et éviterait de réécrire tout le fichier à chaque modification.
3.  **Optimisation Inférence** : Implémenter la quantification (4-bit via `bitsandbytes`) pour charger les modèles plus rapidement et consommer moins de VRAM.

### Fonctionnel
1.  **Feedback Loop** : Ajouter un bouton "Pouce haut/bas" sur les résultats de matching. Ces données pourraient servir à fine-tuner un petit modèle de classification spécifique aux goûts de l'utilisateur plus tard.
2.  **Génération de Lettre de Motivation** : Ajouter une Étape 7 qui utilise le modèle Qwen pour générer une lettre de motivation personnalisée pour une offre sélectionnée, en utilisant le CV et l'offre "matchée" comme contexte.
3.  **Interface de Filtrage** : Permettre de filtrer les résultats finaux par score minimum ou par mots-clés (ex: exclure "ESN" ou "CDD").

### Qualité du Code
*   **Gestion des Erreurs** : Ajouter des blocs `try/except` plus spécifiques autour des appels réseaux ou chargements de modèles pour donner des messages d'erreur plus précis à l'utilisateur.
*   **Configuration** : Déplacer les constantes (noms de modèles, chemins, prompts) dans un fichier `config.py` ou des variables d'environnement.
