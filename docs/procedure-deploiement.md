# Procédure de déploiement — VéloVille V1

Cette procédure cible Windows PowerShell, Python 3.12 et PostgreSQL 14 ou
supérieur. Les commandes sont à exécuter depuis la racine du dépôt. Garder
deux consoles séparées pour l'API et le front. Ne jamais placer de mot de passe
ou de clé JWT dans Git.

## 1. Préparer l'environnement Python

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Dans `.env`, renseigner `DATABASE_URL`, `TEST_DATABASE_URL`, `JWT_SECRET`,
`API_URL` et `API_TIMEOUT_SECONDES`. Générer le secret JWT depuis le venv :

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Copier la sortie dans `.env` uniquement. Pour les URLs PostgreSQL, encoder
les caractères réservés du mot de passe (par exemple `@` en `%40`). L'URL
d'application utilise le schéma SQLAlchemy
`postgresql+psycopg://...`; les commandes `pg_dump` et `pg_restore` emploient
le même compte PostgreSQL via les variables d'environnement du client.

## 2. Créer le rôle et les bases PostgreSQL

Ajouter le dossier `bin` de l'installation PostgreSQL au `PATH` de la session
PowerShell, en adaptant le numéro de version si besoin :

```powershell
$env:Path = "C:\Program Files\PostgreSQL\18\bin;$env:Path"
psql --version
```

Ouvrir une session administrateur PostgreSQL :

```powershell
psql -U postgres
```

Dans `psql`, créer le rôle et les deux bases. Remplacer le mot de passe
exemple par un secret choisi localement, sans le recopier dans un document :

```sql
CREATE ROLE veloville LOGIN PASSWORD 'choisir-un-secret-local';
CREATE DATABASE veloville OWNER veloville;
CREATE DATABASE veloville_test OWNER veloville;
\q
```

Renseigner les URLs correspondantes dans `.env`, puis initialiser le schéma
des deux bases et charger les comptes de recette dans la base applicative :

```powershell
psql -U veloville -d veloville -f sql/schema.sql
psql -U veloville -d veloville -f sql/comptes.sql
psql -U veloville -d veloville_test -f sql/schema.sql
```

**Attention :** `sql/schema.sql` supprime puis recrée les tables. Ne pas
l'exécuter sur une base contenant des données à conserver. Les comptes de
recette sont `exploitant01` et `direction01`; le mot de passe pédagogique
commun est indiqué dans le sujet d'épreuve.

## 3. Importer les données

Depuis la racine et avec `.venv` activé :

```powershell
python scripts/importer.py
```

Le script lit `data/stations.csv`, `data/trajets.csv` et
`data/incidents.csv`, insère dans l'ordre des clés étrangères et écrit le
journal dans `docs/journal_rejets.csv`. Il est rejouable : les conflits de
clé primaire sont ignorés. Vérifier les comptages :

```powershell
psql -U veloville -d veloville -c "SELECT (SELECT count(*) FROM station) AS stations, (SELECT count(*) FROM trajet) AS trajets, (SELECT count(*) FROM incident) AS incidents;"
```

Résultat attendu sur les CSV fournis : `120`, `1998`, `177`.

## 4. Tester et démarrer les services

Lancer les tests depuis la racine :

```powershell
python -m pytest tests --cov=api/services --cov-report=term-missing
```

Démarrer l'API dans une première console :

```powershell
.\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Vérifier l'état de santé :

```powershell
Invoke-RestMethod http://127.0.0.1:8000/sante
```

La réponse attendue est `statut : ok`. Dans une seconde console, démarrer le
front :

```powershell
.\.venv\Scripts\python.exe -m streamlit run front/app.py --server.address 127.0.0.1 --server.port 8501
```

Ouvrir `http://127.0.0.1:8501`, se connecter avec un compte de recette, puis
parcourir Stations, Incidents et Indicateurs. La documentation FastAPI est
disponible à `http://127.0.0.1:8000/docs`.

### Lancer la recette sur `veloville_test`

Le lancement précédent utilise `DATABASE_URL`, donc la base indiquée dans
`.env` (normalement `veloville`). Pour lancer une instance de recette sans
modifier cette base, exécuter l'override ci-dessous dans la console qui
servira à démarrer l'API. L'affectation PowerShell ne vaut que pour cette
console et ses processus enfants ; elle ne change pas `.env` ni une API déjà
lancée dans une autre console.

Depuis la racine du dépôt, dans une première console :

```powershell
$env:DATABASE_URL = & .\.venv\Scripts\python.exe -c "from dotenv import load_dotenv; from pathlib import Path; import os; load_dotenv(Path('.env')); print(os.environ['TEST_DATABASE_URL'])"
& .\.venv\Scripts\python.exe -c "import os; from sqlalchemy.engine import make_url; print(make_url(os.environ['DATABASE_URL']).database)"
```

La deuxième commande doit afficher `veloville_test`. **Ne pas démarrer Uvicorn
si elle affiche `veloville` ou une autre base.** Laisser cette même console
ouverte : l'API héritera de son `DATABASE_URL`.

Si `veloville_test` vient d'être créée ou réinitialisée avec
`sql/schema.sql`, charger les comptes et les données de test une seule fois
après le schéma. Garder le journal d'import hors du dépôt :

```powershell
psql -U veloville -d veloville_test -f sql/comptes.sql
& .\.venv\Scripts\python.exe -c "from pathlib import Path; import os; from scripts.importer import executer_importation; executer_importation(journal_path=Path(os.environ['TEMP']) / 'veloville-test-journal_rejets.csv')"
```

`sql/schema.sql` supprime les tables existantes : ne le relancer que si les
données de la base de test peuvent être effacées. L'import est idempotent ;
il peut être rejoué sans réinitialiser le schéma.

Dans la première console, lancer l'API sur un port distinct :

```powershell
& .\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8001
```

Vérifier `http://127.0.0.1:8001/sante`. Dans une deuxième console, configurer
le front pour appeler cette API et démarrer Streamlit sur un autre port :

```powershell
$env:API_URL = "http://127.0.0.1:8001"
& .\.venv\Scripts\python.exe -m streamlit run front/app.py --server.address 127.0.0.1 --server.port 8502
```

Ouvrir `http://127.0.0.1:8502`. Arrêter les instances de recette avec
`Ctrl+C` dans leurs consoles ; les services standards sur 8000/8501 ne sont
pas concernés.

## 5. Sauvegarder et restaurer

La sauvegarde demande Git Bash et les outils PostgreSQL (`pg_dump`,
`pg_restore`) dans le `PATH`. Depuis PowerShell, ajouter leurs dossiers puis
lancer le script Bash :

```powershell
$env:Path = "C:\Program Files\PostgreSQL\18\bin;C:\Program Files\Git\bin;$env:Path"
& "C:\Program Files\Git\bin\bash.exe" scripts/sauvegarde.sh
```

Le fichier créé se trouve sous `sauvegardes/veloville_AAAAMMJJ_HHMMSS.dump`.
Vérifier que l'archive est lisible :

```powershell
pg_restore --list .\sauvegardes\veloville_AAAAMMJJ_HHMMSS.dump
```

Pour tester une restauration, créer d'abord une base dédiée, sans toucher à
`veloville`. Arrêter l'API et le front de test. Depuis PowerShell, créer la
nouvelle base avec le compte administrateur PostgreSQL :

```powershell
psql -U postgres -d postgres -c "CREATE DATABASE veloville_restore OWNER veloville;"
```

Construire ensuite l'URL libpq de cette base à partir de `DATABASE_URL` dans
`.env`. La commande conserve l'hôte, le port et le compte configurés, mais
remplace explicitement le nom de base :

```powershell
$restoreUrl = & .\.venv\Scripts\python.exe -c "from dotenv import load_dotenv; from pathlib import Path; from sqlalchemy.engine import make_url; import os; load_dotenv(Path('.env')); print(make_url(os.environ['DATABASE_URL']).set(drivername='postgresql', database='veloville_restore').render_as_string(hide_password=False))"
$env:RESTORE_URL = $restoreUrl
& .\.venv\Scripts\python.exe -c "from sqlalchemy.engine import make_url; import os; print('Base de restauration :', make_url(os.environ['RESTORE_URL']).database)"
Remove-Item Env:RESTORE_URL
```

Restaurer dans cette base neuve. Ne pas ajouter `--clean` : la base dédiée
doit être vide, et `CREATE DATABASE` échoue volontairement si elle existe
déjà. Dans ce cas, vérifier son contenu et choisir un autre nom plutôt que
de supprimer des données sans validation.

```powershell
pg_restore --no-owner --dbname="$restoreUrl" .\sauvegardes\veloville_AAAAMMJJ_HHMMSS.dump
psql "$restoreUrl" -c "SELECT (SELECT count(*) FROM station) AS stations, (SELECT count(*) FROM trajet) AS trajets, (SELECT count(*) FROM incident) AS incidents;"
```

Vérifier que les comptages correspondent à ceux de la sauvegarde. Cette
validation cible `veloville_restore` ; elle ne change pas la base applicative
et ne redirige pas l'API en cours. Les commandes de restauration ciblent
explicitement `$restoreUrl` ; ne pas les remplacer par `$env:DATABASE_URL` ni
ajouter `--clean` pour cette vérification.
