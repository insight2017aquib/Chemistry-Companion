# debug_ir.py
from spectra.ir_predictor import predict_ir
import pprint

TARGETS = {
    "Ciprofloxacin":  "OC(=O)c1cn(C2CC2)c2cc(N3CCNCC3)c(F)cc2c1=O",
    "Metronidazole":  "Cc1ncc([N+](=O)[O-])n1CCO",
    "Omeprazole":     "COc1ccc2[nH]c(S(=O)Cc3ncc(C)c(OC)c3C)nc2c1",
}

for name, smi in TARGETS.items():
    print("="*60)
    print(name, smi)
    report = predict_ir(smi)   # IRPredictionReport
    # Show top-level report info
    print("Report type:", type(report))
    try:
        print("Report repr:", repr(report))
    except Exception:
        pass
    # Pretty-print __dict__ if available
    if hasattr(report, "__dict__"):
        pprint.pprint(report.__dict__)
    # Try common attributes for peaks
    peaks = getattr(report, "peaks", None) or getattr(report, "bands", None) or []
    print("Number of peaks returned:", len(peaks))
    for i, p in enumerate(peaks, start=1):
        # print all likely fields
        low_high = getattr(p, "wavenumber_range", getattr(p, "range", getattr(p, "low_high", None)))
        desc = getattr(p, "description", getattr(p, "label", ""))
        fg = getattr(p, "functional_group", getattr(p, "group", ""))
        intensity = getattr(p, "intensity", "")
        print(f"  Peak {i}: group={fg!r}, range={low_high!r}, intensity={intensity!r}, desc={desc!r}")
    # Also search by typical C=N range
    cn_by_range = [p for p in peaks if p and getattr(p, "wavenumber_range", (0,0))[0] >= 1500 and getattr(p, "wavenumber_range", (0,0))[1] <= 1700]
    print("Peaks in 1500-1700 cm^-1 range (possible C=N/C=C):", len(cn_by_range))
    print()
