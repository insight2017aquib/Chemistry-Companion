from spectra.proton_nmr import predictprotonnmr
from spectra.carbon_nmr import predictcarbonnmr
from spectra.ir_predictor import predict_ir


def test_proton_smoke():
    pred = predictprotonnmr("CCO")
    assert pred.is_heuristic is True
    assert pred.n_signals >= 1
    assert isinstance(pred.to_dict(), dict)
    assert isinstance(dict(pred), dict)


def test_carbon_smoke():
    pred = predictcarbonnmr("CC(=O)OC")
    assert pred.is_heuristic is True
    assert pred.total_carbons >= 1
    assert isinstance(pred.to_legacy_dict(), dict)


def test_ir_smoke():
    pred = predict_ir("CC(=O)O")
    assert pred.is_heuristic is True
    assert pred.n_bands >= 1
    assert isinstance(pred.peaks, list)