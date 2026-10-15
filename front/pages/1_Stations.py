import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from front.api_client import ErreurApi, lister_stations, verifier_api

try:
    verifier_api()
except ErreurApi as erreur:
    st.error(str(erreur))
    st.stop()


@st.cache_data(ttl=60)
def charger_stations(jeton: str, commune: str, page: int, taille_page: int):
    return lister_stations(jeton, commune, page, taille_page)


jeton = st.session_state.get("access_token")
if not jeton:
    st.warning("Connectez-vous depuis la page d'accueil pour consulter les stations.")
    st.stop()

st.title("Stations")
commune = st.text_input("Filtrer par commune")
colonne_page, colonne_taille = st.columns(2)
with colonne_page:
    page = st.number_input("Page", min_value=1, value=1, step=1)
with colonne_taille:
    taille_page = st.number_input("Résultats par page", min_value=1, max_value=100, value=20, step=1)

try:
    with st.spinner("Chargement des stations..."):
        resultat = charger_stations(jeton, commune.strip(), int(page), int(taille_page))
    st.caption(f"{resultat['total']} station(s) trouvée(s)")
    if resultat["resultats"]:
        st.dataframe(resultat["resultats"], use_container_width=True, hide_index=True)
        st.caption(f"Page {resultat['page']} · {resultat['taille_page']} résultats par page")
    else:
        st.info("Aucune station ne correspond à ces critères.")
except ErreurApi as erreur:
    st.error(f"Impossible de charger les stations : {erreur}")
