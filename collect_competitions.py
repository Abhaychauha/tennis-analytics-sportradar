"""API 1: /competitions.json  ->  categories + competitions tables."""
from common import bulk_upsert, run_collector

ENDPOINT = "competitions"


def transform(payload):
    """Flatten competitions JSON into (categories, competitions) rows."""
    categories, competitions = {}, []
    for item in payload.get("competitions", []):
        cat = item.get("category") or {}
        if cat.get("id"):
            categories[cat["id"]] = cat.get("name") or "Unknown"
        competitions.append((
            item["id"],
            item.get("name") or "Unknown",
            item.get("parent_id"),
            item.get("type") or "unknown",
            item.get("gender") or "unknown",
            cat.get("id"),
            item.get("level"),
        ))
    return list(categories.items()), competitions


def load(cur, data):
    categories, competitions = data
    bulk_upsert(cur, """
        INSERT INTO categories (category_id, category_name) VALUES %s
        ON CONFLICT (category_id) DO UPDATE
        SET category_name = EXCLUDED.category_name""", categories)
    bulk_upsert(cur, """
        INSERT INTO competitions (competition_id, competition_name, parent_id,
                                  type, gender, category_id, level) VALUES %s
        ON CONFLICT (competition_id) DO UPDATE SET
            competition_name = EXCLUDED.competition_name,
            parent_id = EXCLUDED.parent_id, type = EXCLUDED.type,
            gender = EXCLUDED.gender, category_id = EXCLUDED.category_id,
            level = EXCLUDED.level""", competitions)


if __name__ == "__main__":
    run_collector("Competitions", ENDPOINT, transform, load)
