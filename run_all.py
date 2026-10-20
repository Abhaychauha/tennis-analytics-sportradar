"""Run all three collectors in order (competitions -> complexes -> rankings)."""
import collect_competitions as comps
import collect_complexes as cpx
import collect_doubles_rankings as rank
from common import run_collector

if __name__ == "__main__":
    for name, mod in [("Competitions", comps), ("Complexes", cpx),
                      ("Doubles competitor rankings", rank)]:
        run_collector(name, mod.ENDPOINT, mod.transform, mod.load)
