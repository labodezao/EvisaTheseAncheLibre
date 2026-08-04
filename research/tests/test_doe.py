from banc_recherche.config import Config, DoeConfig
from banc_recherche import doe


def _cfg():
    c = Config()
    c.doe = DoeConfig(sections_mm=(4.0, 8.0), pressures_pa=(600.0, 900.0, 1200.0),
                      clapets_deg=(2.0, 12.0), positions=(0,))
    return c


def test_grid_is_full_factorial():
    combos = list(doe.grid(_cfg()))
    assert len(combos) == 2 * 3 * 2 * 1        # sections × pressions × clapets × positions
    # premier et dernier points attendus (ordre de itertools.product)
    assert combos[0] == (4.0, 600.0, 2.0, 0)
    assert combos[-1] == (8.0, 1200.0, 12.0, 0)


def test_grid_covers_every_combo_once():
    combos = list(doe.grid(_cfg()))
    assert len(set(combos)) == len(combos)     # pas de doublon
