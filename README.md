# VéloVille

API FastAPI et interface Streamlit pour consulter les stations, trajets,
incidents et indicateurs d'un service de vélos en libre-service. Les données
sont stockées dans PostgreSQL et les routes métier sont protégées par JWT.

## Prérequis

- Python 3.12 et PostgreSQL 14 ou supérieur.
- Git; Git Bash et les outils PostgreSQL `pg_dump`/`pg_restore` pour les
  sauvegardes.
- Le dossier `bin` de PostgreSQL doit être dans le `PATH` pour utiliser
  `psql`, `pg_dump` et `pg_restore`.

## Installation

Créer l'environnement depuis la racine du dépôt, sous PowerShell :

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Créer le rôle PostgreSQL et les bases `veloville` et `veloville_test`, puis
renseigner `DATABASE_URL`, `TEST_DATABASE_URL`, `JWT_SECRET`, `API_URL` et
`API_TIMEOUT_SECONDES` dans `.env`. Générer une clé JWT HS256 aléatoire de
32 octets ou plus :

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Ne conserver cette valeur que dans `.env`, ignoré par Git. La procédure
complète, y compris la création de rôle, est dans
[docs/procedure-deploiement.md](docs/procedure-deploiement.md).

Initialiser les bases et comptes :

```powershell
psql -U veloville -d veloville -f sql/schema.sql
psql -U veloville -d veloville -f sql/comptes.sql
psql -U veloville -d veloville_test -f sql/schema.sql
```

**Attention :** `sql/schema.sql` supprime puis recrée les tables; ne pas
l'exécuter sur une base contenant des données à conserver. Importer les CSV :

```powershell
python scripts/importer.py
```

L'import est rejouable et écrit les rejets/avertissements dans
`docs/journal_rejets.csv`.

## Lancement

Dans deux terminaux ouverts à la racine avec `.venv` activé :

```powershell
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
python -m streamlit run front/app.py --server.address 127.0.0.1 --server.port 8501
```

L'API répond sur `http://127.0.0.1:8000`, sa documentation sur
`http://127.0.0.1:8000/docs`, et Streamlit sur `http://127.0.0.1:8501`.
Le front utilise `API_URL` pour joindre l'API.

## Tests

Les tests d'intégration utilisent uniquement `TEST_DATABASE_URL` (base
`veloville_test`) et annulent les changements par rollback.

```powershell
python -m pytest tests --cov=api/services --cov-report=term-missing
```

Dernière mesure locale le 2026-10-14 : **20 tests réussis, 82 % de couverture**
des modules `api/services`. Le résultat peut varier selon les versions des
dépendances et de l'interpréteur.

## Données et schéma

Le MLD, les clés, les contraintes, la correspondance avec RG1 à RG8 et les
volumes de nettoyage mesurés sont décrits dans
[docs/schema-donnees.md](docs/schema-donnees.md). Lors de la dernière
exécution : 120 stations, 1 998 trajets et 177 incidents ont été importés;
35 lignes ont été rejetées et 25 avertissements non bloquants ont été
journalisés.

## Choix écoresponsables

- Les listes sont paginées côté serveur avec une taille maximale de 100.
- Le front ne lance aucun rafraîchissement automatique ni traitement temps réel.
- La liste des stations est mise en cache 60 secondes avec `st.cache_data`.
- Les indicateurs sont calculés par requêtes SQL; le front ne charge pas les
  tables complètes.

## Sauvegarde et restauration

La sauvegarde PostgreSQL en format custom est lancée depuis Git Bash :

```powershell
& "C:\Program Files\Git\bin\bash.exe" scripts/sauvegarde.sh
```

L'archive horodatée est écrite sous `sauvegardes/`. La restauration et les
vérifications sont détaillées dans
[docs/procedure-deploiement.md](docs/procedure-deploiement.md).

## Documentation et limites

- [Schéma et audit des données](docs/schema-donnees.md)
- [Matrice des rôles et droits](docs/matrice-roles-droits.md)
- [Procédure de déploiement](docs/procedure-deploiement.md)
- [Plan de recette](docs/recette/plan-de-recette.md)
- [Résultats de recette](docs/recette/resultats-recette.md)
- [Journal des versions](CHANGELOG.md)

Limites à traiter avant une exploitation durable : la contrainte de capacité
du schéma autorise encore zéro malgré RG1; la cohérence entre `type_usager` et
`usager_ref` n'est pas garantie par l'import; certaines normalisations ne sont
pas inscrites dans le journal; la purge des trajets à 13 mois n'est pas
automatisée. Le transport local utilise HTTP : un déploiement réseau doit
être placé derrière HTTPS.
