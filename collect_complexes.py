"""API 2: /complexes.json  ->  complexes + venues tables."""
from common import bulk_upsert, run_collector

ENDPOINT = "complexes"


def transform(payload):
    """Flatten complexes -> venues (venues are nested inside each complex)."""
    complexes, venues = [], []
    for cpx in payload.get("complexes", []):
        complexes.append((cpx["id"], cpx.get("name") or "Unknown"))
        for ven in cpx.get("venues", []):
            venues.append((
                ven["id"],
                ven.get("name") or "Unknown",
                ven.get("city_name") or "Unknown",
                ven.get("country_name") or "Unknown",
                (ven.get("country_code") or "UNK")[:3],
                ven.get("timezone") or "Unknown",
                cpx["id"],
            ))
    return complexes, venues


def load(cur, data):
    complexes, venues = data
    bulk_upsert(cur, """
        INSERT INTO complexes (complex_id, complex_name) VALUES %s
        ON CONFLICT (complex_id) DO UPDATE
        SET complex_name = EXCLUDED.complex_name""", complexes)
    bulk_upsert(cur, """
        INSERT INTO venues (venue_id, venue_name, city_name, country_name,
                            country_code, timezone, complex_id) VALUES %s
        ON CONFLICT (venue_id) DO UPDATE SET
            venue_name = EXCLUDED.venue_name, city_name = EXCLUDED.city_name,
            country_name = EXCLUDED.country_name,
            country_code = EXCLUDED.country_code,
            timezone = EXCLUDED.timezone, complex_id = EXCLUDED.complex_id""",
                venues)


if __name__ == "__main__":
    run_collector("Complexes", ENDPOINT, transform, load)
