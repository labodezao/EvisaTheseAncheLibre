import pytest

from banc_recherche.cli import build_parser


def test_batch_args():
    ns = build_parser().parse_args(["batch", "camp.hdf5", "--sr", "44100",
                                    "--csv", "out.csv", "--plots", "figs"])
    assert ns.cmd == "batch"
    assert ns.hdf5 == "camp.hdf5"
    assert ns.sr == 44100
    assert ns.csv == "out.csv"
    assert ns.plots == "figs"


def test_batch_defaults():
    ns = build_parser().parse_args(["batch", "camp.hdf5"])
    assert ns.sr == 48000
    assert ns.csv == "plan_exp.csv"
    assert ns.plots is None


def test_subcommand_required():
    with pytest.raises(SystemExit):
        build_parser().parse_args([])


def test_la_commande_justesse_est_branchee():
    ns = build_parser().parse_args(["justesse", "perce.dat", "--sans-jet"])
    assert ns.cmd == "justesse"
    assert ns.dat == "perce.dat"
    assert ns.sans_jet is True
    assert ns.points == 3000


def test_justesse_refuse_poliment_une_perce_sans_doigte(tmp_path, capsys):
    """Sans table des doigtés, il n'y a pas de gamme à juger : on le dit."""
    import pathlib
    from banc_recherche.cli import _cmd_justesse

    p = pathlib.Path(tmp_path) / "nu.dat"
    p.write_text(
        "tube nu\n"
        "NOMBRE DE TRONCONS DE LA LIGNE (-1) N\n0\n"
        "BAS DE LIGNE OUVERT OU FERME C1\n0\n"
        "TABLEAU PERCE D0 (DIMENSION N+1)\n0.015\n"
        "TABLEAU PERCE DL (DIMENSION N+1)\n0.015\n"
        "TABLEAU DES TRONCONS DE LA LIGNE PRINCIPALE L (DIMENSION N+1)\n0.5\n",
        encoding='latin-1')
    ns = build_parser().parse_args(["justesse", str(p)])
    assert _cmd_justesse(ns) == 1
    assert "aucun doigté" in capsys.readouterr().out
