-- 1) Contexte (rôle + warehouse à utiliser) :
USE ROLE ACCOUNTADMIN;
USE WAREHOUSE COMPUTE_WH;

-- 2) Créer la base de travail pour le projet d'anonymisation :
CREATE DATABASE IF NOT EXISTS PII_ANONYMIZATION;
USE DATABASE PII_ANONYMIZATION;

-- 3) Créer les schémas logiques 
--    RAW_DATA      : données sources (documents bruts)
--    PROCESSED_DATA: résultats d'anonymisation et mappings
--    CORTEX_RESULTS: résultats d'analyse LLM (Phi-3):
CREATE SCHEMA IF NOT EXISTS RAW_DATA;
CREATE SCHEMA IF NOT EXISTS PROCESSED_DATA;
CREATE SCHEMA IF NOT EXISTS CORTEX_RESULTS;

-- 4) Créer les tables
-- 4.1 Table des documents bruts (avec PII)
CREATE OR REPLACE TABLE RAW_DATA.FISCAL_DOCUMENTS_RAW (
    DOC_ID INTEGER PRIMARY KEY,
    FILENAME STRING,
    DOCUMENT_TEXT STRING,
    DOCUMENT_TYPE STRING,
    DOC_LENGTH INTEGER,
    LOADED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- 4.2 Table des documents anonymisés 
CREATE OR REPLACE TABLE PROCESSED_DATA.FISCAL_DOCUMENTS_ANON (
    DOC_ID INTEGER PRIMARY KEY,
    ORIGINAL_TEXT STRING,
    ANONYMIZED_TEXT STRING,
    PII_DETECTED VARIANT, -- liste des entités PII détectées (CamemBERT+regex)
    PII_COUNT INTEGER,
    STRATEGY_USED VARIANT, -- stratégie(suppress, perturb, tokenize)
    PROCESSED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- 4.3 Table de mapping pseudonymes && valeurs originales.Pouvoir désanonymiser
CREATE OR REPLACE TABLE PROCESSED_DATA.PII_MAPPING (
    MAPPING_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    PSEUDONYM STRING UNIQUE NOT NULL,
    ORIGINAL_VALUE STRING NOT NULL,
    ENTITY_TYPE STRING, -- type d'entité (PER, ORG, LOC)
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- 4.4 Table des résultats Phi-3

CREATE OR REPLACE TABLE CORTEX_RESULTS.FISCAL_PHI3_ANONYMIZATION (
    DOC_ID INTEGER,                          
    ORIGINAL_TEXT STRING,                   
    LLM_PROMPT STRING,                       -- prompt  envoyé à Phi-3
    LLM_RESPONSE STRING,                     -- réponse brute de Phi-3
    LLM_ANONYMIZED_TEXT STRING,              -- texte anonymisé final 
    MODEL_NAME STRING DEFAULT 'phi-3-mini',  -- nom du modèle utilisé
    TOKENS_USED INTEGER,                     -- consommation (input + output)
    RUN_STATUS STRING,                       -- 'SUCCESS', 'ERROR'
    ERROR_MESSAGE STRING,                    -- message d'erreur éventuel
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);
-- 5) Vérifier le contexte courant et les tables créées
SELECT CURRENT_DATABASE() AS DB, CURRENT_SCHEMA() AS SCHEMA;

SHOW TABLES IN SCHEMA RAW_DATA;
SHOW TABLES IN SCHEMA PROCESSED_DATA;
SHOW TABLES IN SCHEMA CORTEX_RESULTS;



DROP TABLE IF EXISTS CORTEX_RESULTS.LLM_ANALYSIS_RESULTS;
