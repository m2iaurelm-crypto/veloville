from datetime import date, datetime
from typing import Any

from sqlalchemy import text

__all__ = ["activite_par_jour", "incidents_par_statut", "stations_actives"]


def _date_iso(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        text_value = value.strip()
        if not text_value:
            return ""
        if " " in text_value:
            text_value = text_value.split(" ", 1)[0]
        return text_value[:10]
    return str(value)


def activite_par_jour(
    session, date_debut: str | date, date_fin: str | date
) -> list[dict[str, Any]]:
    """Retourne le nombre de trajets par jour pour la période demandée.

    Une ligne est produite uniquement pour les jours ayant au moins un trajet,
    triés par date croissante.
    """
    start = _date_iso(date_debut)
    end = _date_iso(date_fin)
    if not start or not end:
        return []

    rows = (
        session.execute(text("SELECT depart_horodatage FROM trajet")).mappings().all()
    )

    counts: dict[str, int] = {}
    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end)

    for row in rows:
        value = row["depart_horodatage"]
        if value is None:
            continue
        if isinstance(value, str):
            try:
                dt_value = datetime.fromisoformat(value)
            except ValueError:
                try:
                    dt_value = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    continue
        elif isinstance(value, datetime):
            dt_value = value
        elif isinstance(value, date):
            dt_value = datetime.combine(value, datetime.min.time())
        else:
            continue

        day = dt_value.date().isoformat()
        current_date = date.fromisoformat(day)
        if start_date <= current_date <= end_date:
            counts[day] = counts.get(day, 0) + 1

    return [{"jour": day, "nb_trajets": counts[day]} for day in sorted(counts)]


def stations_actives(session, limite: int = 10) -> list[dict[str, Any]]:
    """Retourne les stations les plus actives par total de départs + arrivées."""
    limit = max(int(limite), 1)

    rows = (
        session.execute(
            text(
                """
            WITH mouvements AS (
                SELECT
                    s.station_id,
                    s.nom,
                    SUM(CASE WHEN t.station_depart = s.station_id THEN 1 ELSE 0 END) AS nb_departs,
                    SUM(CASE WHEN t.station_arrivee = s.station_id THEN 1 ELSE 0 END) AS nb_arrivees
                FROM station s
                LEFT JOIN trajet t
                    ON t.station_depart = s.station_id OR t.station_arrivee = s.station_id
                GROUP BY s.station_id, s.nom
            )
            SELECT station_id, nom, nb_departs, nb_arrivees
            FROM mouvements
            WHERE (nb_departs + nb_arrivees) > 0
            ORDER BY (nb_departs + nb_arrivees) DESC, station_id ASC
            LIMIT :limite
            """
            ),
            {"limite": limit},
        )
        .mappings()
        .all()
    )

    return [
        {
            "station_id": row["station_id"],
            "nom": row["nom"],
            "nb_departs": int(row["nb_departs"] or 0),
            "nb_arrivees": int(row["nb_arrivees"] or 0),
        }
        for row in rows
    ]


def incidents_par_statut(session) -> dict[str, Any]:
    """Retourne la répartition des incidents par statut et le délai moyen de résolution."""
    rows = (
        session.execute(
            text(
                """
            SELECT statut, COUNT(*) AS nb_incidents
            FROM incident
            GROUP BY statut
            ORDER BY CASE statut
                WHEN 'ouvert' THEN 1
                WHEN 'en_cours' THEN 2
                WHEN 'resolu' THEN 3
                ELSE 4
            END
            """
            )
        )
        .mappings()
        .all()
    )

    donnees = [
        {"statut": row["statut"], "nb_incidents": int(row["nb_incidents"])}
        for row in rows
    ]

    resolved_rows = (
        session.execute(
            text(
                """
            SELECT date_signalement, date_resolution
            FROM incident
            WHERE statut = 'resolu'
              AND date_signalement IS NOT NULL
              AND date_resolution IS NOT NULL
            """
            )
        )
        .mappings()
        .all()
    )

    deltas = []
    for row in resolved_rows:
        signalement = row["date_signalement"]
        resolution = row["date_resolution"]
        if signalement is None or resolution is None:
            continue
        if isinstance(signalement, str):
            signalement = datetime.fromisoformat(signalement)
        if isinstance(resolution, str):
            resolution = datetime.fromisoformat(resolution)
        delta_seconds = (resolution - signalement).total_seconds()
        if delta_seconds >= 0:
            deltas.append(delta_seconds / 3600)

    delai = round(sum(deltas) / len(deltas), 1) if deltas else None

    return {"donnees": donnees, "delai_moyen_resolution_heures": delai}
