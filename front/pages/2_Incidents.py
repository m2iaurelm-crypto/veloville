import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from front.api_client import ErreurApi, lister_incidents, modifier_statut_incident, verifier_api

try:
    verifier_api()
except ErreurApi as erreur:
    st.error(str(erreur))
    st.stop()

jeton = st.session_state.get("access_token")
role = st.session_state.get("role")
if not jeton:
    st.warning("Connectez-vous depuis la page d'accueil pour consulter les incidents.")
    st.stop()

st.title("Incidents")
statut = st.selectbox("Filtrer par statut", ["Tous", "ouvert", "en_cours", "resolu"])
colonne_page, colonne_taille = st.columns(2)
with colonne_page:
    page = st.number_input("Page", min_value=1, value=1, step=1)
with colonne_taille:
    taille_page = st.number_input("Résultats par page", min_value=1, max_value=100, value=20, step=1)

try:
    with st.spinner("Chargement des incidents..."):
        resultat = lister_incidents(jeton, statut, int(page), int(taille_page))
    st.caption(f"{resultat['total']} incident(s) trouvé(s)")
    incidents = resultat["resultats"]
    if incidents:
        st.dataframe(incidents, use_container_width=True, hide_index=True)
        st.caption(f"Page {resultat['page']} · {resultat['taille_page']} résultats par page")
        if role == "exploitant":
            incidents_modifiables = [
                incident for incident in incidents if incident["statut"] in {"ouvert", "en_cours"}
            ]
            if incidents_modifiables:
                st.subheader("Modifier un statut")
                choix = st.selectbox(
                    "Incident à modifier",
                    incidents_modifiables,
                    format_func=lambda incident: f"{incident['incident_id']} · {incident['statut']}",
                )
                nouveaux_statuts = ["en_cours", "resolu"] if choix["statut"] == "ouvert" else ["resolu"]
                nouveau_statut = st.selectbox("Nouveau statut", nouveaux_statuts)
                if st.button("Enregistrer le statut"):
                    with st.spinner("Mise à jour en cours..."):
                        modifier_statut_incident(jeton, choix["incident_id"], nouveau_statut)
                    st.success("Le statut de l'incident a été mis à jour.")
                    st.rerun()
    else:
        st.info("Aucun incident ne correspond à ces critères.")
except ErreurApi as erreur:
    st.error(f"Impossible de charger ou modifier les incidents : {erreur}")
