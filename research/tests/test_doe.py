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


def test_stroke_grid_fills_both_directions():
    c = _cfg()
    c.doe.use_stroke = True
    c.doe.stroke_speeds = (400.0, 800.0)
    c.doe.stroke_directions = (1, -1)
    combos = list(doe.grid(c))
    # Section(2) × Vitesse(2) × Clapet(2) × Sens(2) = 16
    assert len(combos) == 2 * 2 * 2 * 2
    dirs = {combo[3] for combo in combos}
    assert dirs == {1, -1}                      # pousser ET tirer présents
    # chaque (section, vitesse, clapet) apparaît dans les deux sens
    from collections import Counter
    base = Counter((s, v, c_) for s, v, c_, _ in combos)
    assert all(n == 2 for n in base.values())
