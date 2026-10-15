import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from front.api_client import (
    ErreurApi,
    activite_par_jour,
    incidents_par_statut,
    lister_trajets,
    stations_actives,
    verifier_api,
)

try:
    verifier_api()
except ErreurApi as erreur:
    st.error(str(erreur))
    st.stop()

jeton = st.session_state.get("access_token")
if not jeton:
    st.warning("Connectez-vous depuis la page d'accueil pour consulter les indicateurs.")
    st.stop()

st.title("Indicateurs")
periode = st.date_input("Période d'activité", value=(date(2026, 8, 24), date(2026, 8, 30)))
if len(periode) == 2:
    date_debut, date_fin = periode
else:
    date_debut = date_fin = periode[0]

try:
    with st.spinner("Calcul des indicateurs..."):
        activite = activite_par_jour(jeton, date_debut.isoformat(), date_fin.isoformat())
        total_trajets = lister_trajets(jeton, date_debut.isoformat(), date_fin.isoformat(), page=1, taille_page=1)["total"]
        stations = stations_actives(jeton)
        incidents = incidents_par_statut(jeton)

    delai = incidents["delai_moyen_resolution_heures"]
    colonnes = st.columns(3)
    colonnes[0].metric("Trajets sur la période", total_trajets)
    colonnes[1].metric("Stations actives", len(stations["donnees"]))
    colonnes[2].metric("Délai moyen de résolution", "Non disponible" if delai is None else f"{delai:.1f} h")

    st.subheader("Trajets par jour")
    if activite["donnees"]:
        st.dataframe(activite["donnees"], use_container_width=True, hide_index=True)
    else:
        st.info("Aucun trajet sur cette période.")

    st.subheader("Stations les plus actives")
    if stations["donnees"]:
        st.dataframe(stations["donnees"], use_container_width=True, hide_index=True)
    else:
        st.info("Aucune station active.")

    st.subheader("Incidents par statut")
    if incidents["donnees"]:
        st.dataframe(incidents["donnees"], use_container_width=True, hide_index=True)
    else:
        st.info("Aucun incident enregistré.")
except ErreurApi as erreur:
    st.error(f"Impossible de charger les indicateurs : {erreur}")
