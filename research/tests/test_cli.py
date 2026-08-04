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
