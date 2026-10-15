-- Schéma de la base veloville (PostgreSQL 14+).
-- À compléter en respectant le contrat du sujet (types, clés, contraintes).
-- Le script doit être rejouable : prévoir les DROP ... IF EXISTS ou
-- CREATE TABLE IF NOT EXISTS.

-- Suppression dans l'ordre inverse des dépendances pour éviter les erreurs de clés étrangères
DROP TABLE IF EXISTS trajet CASCADE;
DROP TABLE IF EXISTS incident CASCADE;
DROP TABLE IF EXISTS station CASCADE;
DROP TABLE IF EXISTS utilisateur CASCADE;

-- ---------------------------------------------------------------
-- 1. Table station
-- ---------------------------------------------------------------
CREATE TABLE station (
    station_id VARCHAR(10) PRIMARY KEY,
    nom VARCHAR(100) NOT NULL,
    commune VARCHAR(100) NOT NULL,
    capacite INTEGER NOT NULL CHECK (capacite > 0),
	latitude NUMERIC(8,5) NOT NULL,
	longitude NUMERIC(8,5) NOT NULL,
	date_mise_en_service DATE NOT NULL
);

-- ---------------------------------------------------------------
-- 2. Table trajet
-- ---------------------------------------------------------------
CREATE TABLE trajet (
    trajet_id VARCHAR(12) PRIMARY KEY,
    velo_id VARCHAR(8) NOT NULL,
    depart_horodatage TIMESTAMP NOT NULL,
    station_depart VARCHAR(10) NOT NULL REFERENCES station(station_id),
    station_arrivee VARCHAR(10) REFERENCES station(station_id),
    duree_secondes INTEGER NOT NULL CHECK (duree_secondes > 0),
    type_usager VARCHAR(50) NOT NULL
        CHECK (type_usager IN ('abonne', 'occasionnel')),
    usager_ref VARCHAR(50)
);

-- ---------------------------------------------------------------
-- 3. Table incident
-- ---------------------------------------------------------------
CREATE TABLE incident (
    incident_id VARCHAR(12) PRIMARY KEY,
    date_signalement TIMESTAMP NOT NULL,
    cible VARCHAR(50) NOT NULL
        CHECK (cible IN ('velo', 'station')),
    velo_id VARCHAR(8),
    station_id VARCHAR(10) NULL REFERENCES station(station_id),
    type_incident VARCHAR(50) NOT NULL,
    statut VARCHAR(20) NOT NULL CHECK (statut IN ('ouvert', 'en_cours', 'resolu')),
    date_resolution TIMESTAMP,
    technicien VARCHAR(100),
    CONSTRAINT ck_incident_cible_reference CHECK (
        (cible = 'velo' AND velo_id IS NOT NULL AND station_id IS NULL)
        OR (cible = 'station' AND velo_id IS NULL AND station_id IS NOT NULL)
    ),
    CONSTRAINT ck_incident_resolution_statut CHECK (
        (statut = 'resolu') = (date_resolution IS NOT NULL)
    ),
    CONSTRAINT ck_incident_resolution_apres_signalement CHECK (
        date_resolution IS NULL OR date_resolution >= date_signalement
    )
);

-- ---------------------------------------------------------------
-- 4. Table utilisateur
-- ---------------------------------------------------------------
CREATE TABLE utilisateur (
    id_utilisateur SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    mot_de_passe_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('exploitant', 'direction'))
);

-- ---------------------------------------------------------------
-- 5. Index utiles aux filtres et aux indicateurs
-- ---------------------------------------------------------------

-- Optimisation des recherches sur les trajets 
CREATE INDEX idx_trajet_depart_horodatage ON trajet(depart_horodatage);
CREATE INDEX idx_trajet_station_depart ON trajet(station_depart);
CREATE INDEX idx_trajet_station_arrivee ON trajet(station_arrivee);

-- Optimisation du suivi des incidents
CREATE INDEX idx_incident_statut ON incident(statut);
CREATE INDEX idx_incident_station_id ON incident(station_id);

-- Optimisation de la recherche des stations par commune
CREATE INDEX idx_station_commune ON station(commune);