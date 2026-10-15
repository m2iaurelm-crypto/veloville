import requests
import pytest

from front.api_client import ErreurApi, verifier_api


def test_verifier_api_signale_une_indisponibilite_en_francais(monkeypatch):
    def requete_indisponible(*args, **kwargs):
        raise requests.ConnectionError("connexion refusée")

    monkeypatch.setattr("front.api_client.requests.request", requete_indisponible)

    with pytest.raises(ErreurApi, match="API injoignable"):
        verifier_api()