# Game Analytics: Unlocking Tennis Data with Sportradar API

Python + PostgreSQL + Streamlit.

## The 3 APIs (Tennis v3)
| PDF step | Script | Endpoint | Tables filled |
|---|---|---|---|
| 1. Competitions | `collect_competitions.py` | `/tennis/{access}/v3/{lang}/competitions.json` | categories, competitions |
| 2. Complexes | `collect_complexes.py` | `/tennis/{access}/v3/{lang}/complexes.json` | complexes, venues |
| 3. Doubles rankings | `collect_doubles_rankings.py` | `/tennis/{access}/v3/{lang}/double_competitors_rankings.json` | competitors, competitor_rankings |

## Setup
1. `pip install -r requirements.txt`
2. `createdb tennis_db` then `psql -d tennis_db -f schema.sql`
3. Copy `.env.example` to `.env`; paste your Sportradar key (one key for all 3 APIs) and your Postgres login
4. Collect data: `python run_all.py` (or run each `collect_*.py` on its own)
5. Launch: `streamlit run app.py`
6. All SQL analysis queries are in `queries.sql`

## Notes
- Trial keys allow ~1 request/second; `common.py` sleeps between calls and retries on HTTP 429.
- Extra columns beyond the PDF: `competitions.level`, and `ranking_year / ranking_week / gender` on `competitor_rankings`.
- Doubles "competitors" can be teams (e.g. `Glasspool L / Middelkoop M`), per the Sportradar docs.
- Rankings update weekly (Mondays); re-run `collect_doubles_rankings.py` to add a new week.
