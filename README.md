# 🔐 RGPD – Anonymisation de Notes Fiscales

## Table des matières 📚
1. [Présentation du projet](#présentation-du-projet)
2. [Cas d’usage](#cas-dusage)
3. [Architecture](#architecture)
4. [Expérimentations / Modèles](#expérimentations--modèles)
5. [Interface Utilisateur](#interface-utilisateur)
6. [Comment exécuter le projet](#comment-exécuter-le-projet)
7. [Défis rencontrés](#défis-rencontrés)
8. [Contribuer](#contribuer)

---

## Présentation du projet

Ce projet permet d’**anonymiser automatiquement les notes fiscales** en conformité avec le **RGPD**.  
Il détecte et remplace les informations personnelles (PII) comme :

- Noms et prénoms
- Dates de naissance / âge
- Adresses, codes postaux, villes
- Emails et numéros de téléphone
- IBAN, SIREN, SIRET
- Revenus et montants financiers

Le projet génère deux fichiers :

1. **Note fiscale anonymisée**  
2. **Mapping chiffré** entre données originales et anonymisées  

---

## Cas d’usage

- Entreprises souhaitant partager des documents fiscaux sans divulguer les informations personnelles.  
- Audit interne ou externe avec données anonymisées.  
- Préparation de jeux de données pour tests ou machine learning.  

**Exemple concret :**

- Original : `Pierre ROLLO, SIRET: 12345678901234, IBAN: FR76 ...`  
- Après anonymisation : `Louis DUPONT, SIRET: 98765432109876, IBAN: FR12 ...`  

---

## Architecture

```text
project/
├── backend/
│ ├── app.py # API FastAPI pour anonymisation
│ ├── requirements.txt
│ └── outputs/ # Fichiers générés
├──notebooks
│  ├──01_generate_synthetic_data.ipynb
│  ├──02_load_real_documents.ipynb
│  ├──03_ner_detection.ipynb
│  ├──04_anonymization_pipeline.ipynb
│  ├──05_anonymization_phi3_comparison.ipynb
├── frontend/
│ └── index.html # Interface web simple HTML/JS
├──scripts
│  ├──01_setup_db.sql
├── Dockerfile
├── docker-compose.yml
└── .env # Variables d’environnement (FERNET_KEY)
```


- **Backend** : FastAPI, CamemBERT NER, regex PII, phi3, chiffrement Fernet  
- **Frontend** : HTML + JS pour upload / download  
- **Docker** : Conteneurs séparés pour backend et frontend  
- **Env** : `.env` pour clés et secrets  

---

## Expérimentations / Modèles

- **CamemBERT NER** (`Jean-Baptiste/camembert-ner-with-dates`) pour identifier les entités  
- **Regex custom** pour SIRET, IBAN, TVA, emails, téléphones  
- **Faker** pour générer des données de substitution  
- **Cryptography / Fernet** pour mapping chiffré  

---

## Interface Utilisateur

- Page web simple pour déposer un fichier `.docx`  
- Bouton `Anonymiser` → traitement backend  
- Section `Téléchargement` pour récupérer :

  1. Note fiscale anonymisée  
  2. Mapping chiffré  

**Capture d’écran exemple :**

[ 🔐 Anonymisation RGPD – Note Fiscale ]
[ Choisir un fichier DOCX ]
[ Bouton Anonymiser ]
[ Téléchargement : Note Anonymisée | Mapping RGPD ]


---

## Comment exécuter le projet

### 1️⃣ Avec Python local

```bash
# Créer et activer le venv
python3 -m venv venv
source venv/bin/activate

# Installer dépendances
cd backend
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m spacy download fr_core_news_lg

# Ajouter FERNET_KEY dans .env à la racine
echo "FERNET_KEY=$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')" > ../.env

# Lancer backend
uvicorn app:app --reload

# Ouvrir frontend
# http://localhost:8000 ou http://localhost:8080 si Docker
2️⃣ Avec Docker
bash
Copier le code
docker-compose build
docker-compose up