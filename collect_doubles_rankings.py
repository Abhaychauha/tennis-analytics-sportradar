"""API 3: /double_competitors_rankings.json -> competitors + competitor_rankings."""
from common import bulk_upsert, run_collector

ENDPOINT = "double_competitors_rankings"


def transform(payload):
    """Flatten rankings -> competitor_rankings -> competitor."""
    competitors, rankings = {}, []
    for block in payload.get("rankings", []):          # one block per ATP / WTA
        gender, year, week = block.get("gender"), block.get("year"), block.get("week")
        for row in block.get("competitor_rankings", []):
            comp = row.get("competitor") or {}
            if not comp.get("id"):
                continue
            competitors[comp["id"]] = (
                comp["id"],
                comp.get("name") or "Unknown",
                comp.get("country") or "Unknown",
                (comp.get("country_code") or "UNK")[:3],
                (comp.get("abbreviation") or "UNK")[:10],
            )
            rankings.append((
                row.get("rank") or 0,
                row.get("movement") or 0,
                row.get("points") or 0,
                row.get("competitions_played") or 0,
                comp["id"], year, week, gender,
            ))
    return list(competitors.values()), rankings


def load(cur, data):
    competitors, rankings = data
    bulk_upsert(cur, """
        INSERT INTO competitors (competitor_id, name, country, country_code,
                                 abbreviation) VALUES %s
        ON CONFLICT (competitor_id) DO UPDATE SET
            name = EXCLUDED.name, country = EXCLUDED.country,
            country_code = EXCLUDED.country_code,
            abbreviation = EXCLUDED.abbreviation""", competitors)
    bulk_upsert(cur, """
        INSERT INTO competitor_rankings ("rank", movement, points,
               competitions_played, competitor_id, ranking_year,
               ranking_week, gender) VALUES %s
        ON CONFLICT (competitor_id, ranking_year, ranking_week, gender)
        DO UPDATE SET "rank" = EXCLUDED."rank", movement = EXCLUDED.movement,
               points = EXCLUDED.points,
               competitions_played = EXCLUDED.competitions_played""", rankings)


if __name__ == "__main__":
    run_collector("Doubles competitor rankings", ENDPOINT, transform, load)
