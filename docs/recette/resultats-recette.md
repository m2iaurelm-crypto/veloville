# Résultats de recette

## Relevé d'exécution

| Cas | Date et heure | Version testée (commit ou tag) | Statut | Preuve | Anomalie |
|---|---|---|---|---|---|
| REC-01 | 2026-10-15 | dépôt local / `veloville_test` | OK | Import exécuté deux fois : 120 stations, 1 998 trajets et 177 incidents après chaque passage ; la base était vide avant le premier. | Aucune |
| REC-02 | 2026-10-15 | dépôt local / `veloville_test` | OK | Journal temporaire : 60 lignes, les six colonnes présentes et renseignées (`NULL` explicite pour les valeurs absentes). Volumes réconciliés : stations 120 = 120 importées ; trajets 2 030 = 1 998 importés + 20 rejetés + 12 doublons ; incidents 180 = 177 importés + 3 rejetés. Requête des arrivées orphelines : 0. | Aucune |
| REC-03 | 2026-10-15 | dépôt local / `veloville_test` | OK | `POST /auth/login` : 200 avec jeton non vide et rôle attendu pour `exploitant01` et `direction01`. | Aucune |
| REC-04 | 2026-10-15 | dépôt local / `veloville_test` | KO | Avec le scénario prescrit, `mauvais` retourne 422 (mot de passe de moins de 8 caractères), tandis que l’utilisateur inconnu retourne 401. Contrôle complémentaire avec `mauvais123` : les deux réponses sont 401 `Identifiants invalides`. | [ANO-001](anomalies/ANO-001.md) |
| REC-05 | 2026-10-15 | dépôt local / `veloville_test` | OK | `GET /stations` sans jeton et avec jeton invalide : 401 ; `GET /sante` : 200 `{"statut":"ok"}`. | Aucune |
| REC-06 | 2026-10-15 | dépôt local / `veloville_test` | OK | `I2026-0002` : direction refusée (403), statut inchangé ; exploitant accepté (200), seconde transition refusée (422). La mise à jour exploitant est ensuite annulée par rollback en base de test. | Aucune |
| REC-07 | 2026-10-15 | dépôt local / `veloville_test` | OK | Page 1 : total 120, 50 résultats, premier `S001` ; page 3 : 20 résultats ; Lille : total 46 ; page 0 et taille 101 : 422. | Aucune |
| REC-08 | 2026-10-15 | dépôt local / `veloville_test` | OK | `GET /stations/S001` : 200, « Lille - Gare » ; `GET /stations/S999` : 404 « Station introuvable ». | Aucune |
| REC-09 | 2026-10-15 | dépôt local / `veloville_test` | OK | Activité API identique à la requête SQL du 24 au 30 août 2026 ; somme 1 998, égale au total de `/trajets`. | Aucune |
| REC-10 | 2026-10-15 | dépôt local / front Streamlit + API sur `veloville_test` | OK | Page 7 Stations : état vide conforme. API arrêtée puis F5 : le contrôle `GET /sante` affiche « API injoignable. Vérifiez que le service est démarré. » avant le contrôle de session ; Indicateurs et l’accueil affichent aussi ce message, sans traceback. API redémarrée, reconnexion effectuée : Stations affiche de nouveau 120 stations. | [ANO-002 corrigée](anomalies/ANO-002.md) |

## Synthèse

- 10 cas prévus sur le plan de recette.
- 10 cas exécutés le 15/10/2026 sur la base isolée `veloville_test`.
- 9 OK, 1 KO, 0 NT.
- 1 anomalie ouverte et 1 corrigée puis rejouée OK (ANO-001 ouverte ; ANO-002 corrigée).
- Les imports, les contrôles d’accès, la pagination, l’agrégation et la gestion d’indisponibilité API après F5 sont validés. REC-04 reste KO avec la valeur de mot de passe trop courte prescrite par le plan.

## Axes d’amélioration

1. Remplacer dans REC-04 le mot de passe erroné par une valeur d’au moins 8 caractères, puis rejouer le cas.
2. Conserver le journal temporaire de campagne et les preuves des contrôles front comme éléments reproductibles.

## Procès-verbal de recette

# Procès-verbal de recette — VéloVille V1, rejeu du 15/10/2026

## 1. Identification
Application : VéloVille API + front Streamlit. Version testée : dépôt local non étiqueté, base isolée `veloville_test`. Date : 2026-10-15. Environnement : Windows, Python 3.14.7, PostgreSQL, dépendances de `.venv`.

## 2. Périmètre recetté
Les dix cas REC-01 à REC-10 ont été rejoués sur la base isolée. REC-06 a été annulé par rollback après vérification. REC-10 a été observé dans le navigateur avec l’API et le front démarrés localement.

## 3. Résultats de la campagne
10 cas prévus. 10 exécutés : 9 OK, 1 KO, 0 NT.
Anomalies : 1 ouverte (ANO-001), 1 corrigée et rejouée OK (ANO-002).

## 4. Réserves bloquantes
Aucune réserve bloquante identifiée.

## 5. Réserves non bloquantes
- ANO-001 — la valeur `mauvais` de REC-04 est rejetée en 422 avant l’authentification ; remplacer par une valeur erronée d’au moins 8 caractères et rejouer le cas.

## 6. Décision
Décision à prononcer par le commanditaire. REC-10 est conforme après correction et rejeu ; REC-04 reste la seule réserve non bloquante à arbitrer.

## 7. Signatures
Pour le commanditaire — ____________________
Pour le développeur — ____________________  Date : 2026-10-15
