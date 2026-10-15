# Matrice des rôles et des droits

Les routes métier exigent un jeton Bearer valide. Le rôle est relu depuis la
base après validation du jeton ; le rôle porté par le client Streamlit ne
remplace jamais ce contrôle serveur.

| Méthode et route | Anonyme | Exploitant | Direction |
|---|---|---|---|
| `GET /sante` | 200 | 200 | 200 |
| `POST /auth/login` | 200 avec identifiants valides ; 401 sinon | 200 avec identifiants valides ; 401 sinon | 200 avec identifiants valides ; 401 sinon |
| `GET /stations` | 401 | 200 | 200 |
| `GET /stations/{station_id}` | 401 | 200 ; 404 si introuvable | 200 ; 404 si introuvable |
| `GET /trajets` | 401 | 200 ; `usager_ref` disponible pour le support | 200 ; `usager_ref` renvoyé à `null` |
| `GET /incidents` | 401 | 200 | 200 |
| `PUT /incidents/{incident_id}/statut` | 401 | 200 si transition valide ; 404/422 sinon | 403 `Acces reserve au role exploitant` |
| `GET /indicateurs/activite-par-jour` | 401 | 200 | 200 |
| `GET /indicateurs/stations-actives` | 401 | 200 | 200 |
| `GET /indicateurs/incidents-par-statut` | 401 | 200 | 200 |

Un jeton absent, invalide ou expiré produit une réponse 401 sur les routes
protégées. Les identifiants incorrects renvoient le même message 401, que le
nom d'utilisateur existe ou non. Le contrôle d'accès au PUT est réalisé dans
l'API ; masquer son bouton dans Streamlit n'est qu'une amélioration d'interface.

## Données sensibles

- **Mots de passe** : seule l'empreinte bcrypt est stockée dans
	`utilisateur.mot_de_passe_hash`. Le mot de passe en clair est utilisé pour
	vérifier le login, jamais conservé dans `st.session_state` ni journalisé.
- **`usager_ref`** : pseudonyme de l'abonné, non directement identifiant mais
	à traiter comme une donnée personnelle pseudonymisée. Il n'existe pas de
	table de correspondance dans l'application. L'API ne renvoie pas sa valeur
	au rôle `direction` (champ `null`) ; elle reste disponible à `exploitant`
	pour le support. Les écrans actuels ne présentent pas les trajets détaillés.
- **Jeton JWT** : signé en HS256, avec `sub`, `role`, `iat` et `exp` (60 minutes).
	La signature et l'expiration sont vérifiées par l'API, puis l'utilisateur et
	son rôle sont relus en base. Le jeton reste dans la session Streamlit, n'est
	ni affiché ni ajouté à une URL ; les appels le transmettent dans l'en-tête
	`Authorization`.
- **Configuration** : `DATABASE_URL` et `JWT_SECRET` sont lus depuis
	l'environnement ou `.env`. `.env` est ignoré par Git ; `.env.example` ne
	contient ni mot de passe réel ni clé JWT. La clé doit être générée
	aléatoirement (32 octets minimum), jamais copiée depuis un exemple public.
- **Transport** : le développement local utilise HTTP sur la boucle locale.
	Tout déploiement sur un réseau doit être placé derrière HTTPS afin de
	protéger les identifiants et les jetons en transit.

La durée de conservation cible des trajets détaillés est de 13 mois selon le
cahier des charges. La purge automatique n'est pas encore mise en œuvre dans
cette version ; elle reste une limite à traiter avant une exploitation durable.
