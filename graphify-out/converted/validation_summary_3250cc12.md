<!-- converted from validation_summary.xlsx -->

## Sheet: Executive Summary
| Spectra Validation Report  |  Heuristic Predictions vs Experimental Reference |  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Generated: 2026-05-20 22:12   |   Source: data\spectra_benchmark.csv   |   Molecules: 61   |   NOTE: All predictions are HEURISTIC (rule-based, approximate) |  |  |  |  |  |  |  |
| Matching Tolerances Used |  |  |  |  |  |  |  |
| IR
±50.0 | 1H NMR
±0.5 | 13C NMR
±5.0 |  |  |  |  |  |
| Domain | Avg MAE | Avg RMSE | Coverage [HEURISTIC] | Coverage [EXPERIMENTAL] | Total Matches | Records OK | Records Failed |
| IR | 17.9972 | 21.4274 | 85.8% | 85.8% | 302 | 61 | 0 |
| 1H NMR | 0.2137 | 0.2285 | 98.2% | 50.6% | 143 | 61 | 0 |
| 13C NMR | 2.1507 | 2.4126 | 96.3% | 59.4% | 207 | 61 | 0 |
| DISCLAIMER: All spectral predictions are HEURISTIC (rule-based). Reference 'experimental' values are HEURISTIC-DERIVED (prediction + Gaussian noise). Not suitable for regulatory or publication use without independent verification. |  |  |  |  |  |  |  |
## Sheet: IR Validation
| IR Validation  |  [HEURISTIC] Predicted  vs  [EXPERIMENTAL] Reference |  |  |  |  |  |  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Compound | SMILES | Predicted Peaks [HEURISTIC] | Experimental Peaks [EXPERIMENTAL] | Matched | MAE | RMSE | Coverage [HEURISTIC] | Coverage [EXPERIMENTAL] | Missing (FN) | Extra (FP) | Tolerance | Status |
| Benzene | c1ccccc1 | 3 | 3 | 3 | 3.5667 | 3.6217 | 100.0% | 100.0% | 0 | 0 | ±50.0 | OK |
| Toluene | Cc1ccccc1 | 4 | 4 | 4 | 16.3375 | 20.9594 | 100.0% | 100.0% | 0 | 0 | ±50.0 | OK |
| Nitrobenzene | O=[N+]([O-])c1ccccc1 | 5 | 5 | 4 | 19.1450 | 19.4296 | 80.0% | 80.0% | 1 | 1 | ±50.0 | OK |
| Chlorobenzene | Clc1ccccc1 | 4 | 4 | 4 | 14.4575 | 14.6701 | 100.0% | 100.0% | 0 | 0 | ±50.0 | OK |
| Bromobenzene | Brc1ccccc1 | 4 | 4 | 4 | 18.5125 | 22.6245 | 100.0% | 100.0% | 0 | 0 | ±50.0 | OK |
| Fluorobenzene | Fc1ccccc1 | 4 | 4 | 4 | 11.4800 | 13.5558 | 100.0% | 100.0% | 0 | 0 | ±50.0 | OK |
| Iodobenzene | Ic1ccccc1 | 4 | 4 | 4 | 22.0125 | 23.3447 | 100.0% | 100.0% | 0 | 0 | ±50.0 | OK |
| Anisole | COc1ccccc1 | 6 | 6 | 5 | 12.2320 | 13.7398 | 83.3% | 83.3% | 1 | 1 | ±50.0 | OK |
| Ethyl acetate | CCOC(C)=O | 6 | 6 | 6 | 21.4183 | 26.6312 | 100.0% | 100.0% | 0 | 0 | ±50.0 | OK |
| Methyl benzoate | COC(=O)c1ccccc1 | 9 | 9 | 8 | 14.9775 | 19.3565 | 88.9% | 88.9% | 1 | 1 | ±50.0 | OK |
| Acetamide | CC(N)=O | 5 | 5 | 4 | 13.3400 | 19.1955 | 80.0% | 80.0% | 1 | 1 | ±50.0 | OK |
| Benzamide | NC(=O)c1ccccc1 | 7 | 7 | 7 | 19.0614 | 22.3814 | 100.0% | 100.0% | 0 | 0 | ±50.0 | OK |
| Pyridine | c1ccncc1 | 3 | 3 | 2 | 23.3150 | 32.9229 | 66.7% | 66.7% | 1 | 1 | ±50.0 | OK |
| Pyrrole | c1cc[nH]c1 | 0 | 0 | 0 | N/A | N/A | 0.0% | 0.0% | 0 | 0 | ±50.0 | OK |
| Furan | c1ccoc1 | 0 | 0 | 0 | N/A | N/A | 0.0% | 0.0% | 0 | 0 | ±50.0 | OK |
| Thiophene | c1ccsc1 | 0 | 0 | 0 | N/A | N/A | 0.0% | 0.0% | 0 | 0 | ±50.0 | OK |
| Indole | c1ccc2[nH]ccc2c1 | 3 | 3 | 3 | 17.5933 | 20.1535 | 100.0% | 100.0% | 0 | 0 | ±50.0 | OK |
| Quinoline | c1ccc2ncccc2c1 | 6 | 6 | 6 | 20.1117 | 22.1896 | 100.0% | 100.0% | 0 | 0 | ±50.0 | OK |
| Imidazole | c1c[nH]cn1 | 0 | 0 | 0 | N/A | N/A | 0.0% | 0.0% | 0 | 0 | ±50.0 | OK |
| Pyrimidine | c1cncnc1 | 3 | 3 | 3 | 19.4233 | 22.7400 | 100.0% | 100.0% | 0 | 0 | ±50.0 | OK |
| Purine | c1nc2[nH]cnc2[nH]1 | 0 | 0 | 0 | N/A | N/A | 0.0% | 0.0% | 0 | 0 | ±50.0 | OK |
| Benzoxazole | c1ccc2ocnc2c1 | 3 | 3 | 3 | 16.9267 | 26.7033 | 100.0% | 100.0% | 0 | 0 | ±50.0 | OK |
| Quinoxaline | c1ccc2c(c1)nc1ccccn12 | 6 | 6 | 5 | 12.1160 | 15.3184 | 83.3% | 83.3% | 1 | 1 | ±50.0 | OK |
| Ethanol | CCO | 4 | 4 | 4 | 19.8075 | 25.3707 | 100.0% | 100.0% | 0 | 0 | ±50.0 | OK |
| Ethyl methyl ether | CCOC | 3 | 3 | 3 | 22.6733 | 27.9852 | 100.0% | 100.0% | 0 | 0 | ±50.0 | OK |
| Diethyl ether | CCOCC | 3 | 3 | 3 | 12.4700 | 14.2675 | 100.0% | 100.0% | 0 | 0 | ±50.0 | OK |
| Methyl tert-butyl ether | COC(C)(C)C | 3 | 3 | 3 | 20.6867 | 25.8858 | 100.0% | 100.0% | 0 | 0 | ±50.0 | OK |
| Aspirin | CC(=O)Oc1ccccc1C(=O)O | 16 | 16 | 16 | 16.2306 | 18.4306 | 100.0% | 100.0% | 0 | 0 | ±50.0 | OK |
| Benzyl acetate | CC(=O)OCc1ccccc1 | 9 | 9 | 9 | 9.3867 | 11.4469 | 100.0% | 100.0% | 0 | 0 | ±50.0 | OK |
| N-Methylacetamide | CNC(C)=O | 5 | 5 | 4 | 14.4150 | 24.6043 | 80.0% | 80.0% | 1 | 1 | ±50.0 | OK |
| Nicotinamide | NC(=O)c1ccncc1 | 7 | 7 | 7 | 22.7114 | 24.3241 | 100.0% | 100.0% | 0 | 0 | ±50.0 | OK |
| Phenol | Oc1ccccc1 | 9 | 9 | 9 | 13.4933 | 17.9941 | 100.0% | 100.0% | 0 | 0 | ±50.0 | OK |
| Aniline | Nc1ccccc1 | 3 | 3 | 3 | 40.1100 | 40.6630 | 100.0% | 100.0% | 0 | 0 | ±50.0 | OK |
| Nitropropane | CCC[N+](=O)[O-] | 3 | 3 | 3 | 6.5500 | 7.9225 | 100.0% | 100.0% | 0 | 0 | ±50.0 | OK |
| 2-Chloropyridine | Clc1ccccn1 | 4 | 4 | 4 | 14.2600 | 16.3003 | 100.0% | 100.0% | 0 | 0 | ±50.0 | OK |
| 4-Nitrophenol | O=[N+]([O-])c1ccc(O)cc1 | 11 | 11 | 11 | 13.9545 | 17.9452 | 100.0% | 100.0% | 0 | 0 | ±50.0 | OK |
| 2-Chloroethylamine | NCCCl | 5 | 5 | 5 | 16.2700 | 20.1769 | 100.0% | 100.0% | 0 | 0 | ±50.0 | OK |
| 2-Bromoethanol | OCCBr | 5 | 5 | 4 | 26.8775 | 27.3739 | 80.0% | 80.0% | 1 | 1 | ±50.0 | OK |
| 4-Chloroanisole | COc1ccc(Cl)cc1 | 7 | 7 | 6 | 26.4467 | 29.3623 | 85.7% | 85.7% | 1 | 1 | ±50.0 | OK |
| 1,4-Dioxane | C1COCCO1 | 5 | 5 | 5 | 17.8820 | 23.7361 | 100.0% | 100.0% | 0 | 0 | ±50.0 | OK |
| 1,3,5-Triazine | c1ncncn1 | 3 | 3 | 3 | 25.7333 | 29.9478 | 100.0% | 100.0% | 0 | 0 | ±50.0 | OK |
| Benzimidazole | c1ccc2[nH]cnc2c1 | 3 | 3 | 3 | 16.5633 | 20.8682 | 100.0% | 100.0% | 0 | 0 | ±50.0 | OK |
| Coumarin | O=C1CC=Cc2ccccc2O1 | 12 | 12 | 12 | 16.3217 | 21.0216 | 100.0% | 100.0% | 0 | 0 | ±50.0 | OK |
| Naphthalene | c1ccc2ccccc2c1 | 6 | 6 | 6 | 13.1917 | 16.3465 | 100.0% | 100.0% | 0 | 0 | ±50.0 | OK |
| Phenanthrene | c1ccc2cc3ccccc3cc2c1 | 9 | 9 | 8 | 12.9763 | 15.8203 | 88.9% | 88.9% | 1 | 1 | ±50.0 | OK |
| Indene | C1=Cc2ccccc2C1 | 7 | 7 | 7 | 16.7529 | 20.9252 | 100.0% | 100.0% | 0 | 0 | ±50.0 | OK |
| Quinazoline | c1ccc2nccc-2nc1 | 0 | 0 | 0 | N/A | N/A | 0.0% | 0.0% | 0 | 0 | ±50.0 | OK |
| Isoquinoline | c1ccc2cnccc2c1 | 6 | 6 | 5 | 21.5860 | 23.1618 | 83.3% | 83.3% | 1 | 1 | ±50.0 | OK |
| 1,4-Dimethoxybenzene | COc1ccc(OC)cc1 | 8 | 8 | 7 | 27.0000 | 30.8566 | 87.5% | 87.5% | 1 | 1 | ±50.0 | OK |
| Cyclohexanone | O=C1CCCCC1 | 3 | 3 | 3 | 14.7267 | 17.2565 | 100.0% | 100.0% | 0 | 0 | ±50.0 | OK |
| 2,4,6-Trinitrotoluene | Cc1c([N+](=O)[O-])cc([N+](=O)[O-])cc1[N+](=O)[O-] | 10 | 10 | 9 | 17.2744 | 22.2422 | 90.0% | 90.0% | 1 | 1 | ±50.0 | OK |
| 4-Vinylpyridine | C=Cc1ccncc1 | 6 | 6 | 6 | 21.3900 | 24.5397 | 100.0% | 100.0% | 0 | 0 | ±50.0 | OK |
| 2-Methylfuran | Cc1ccoc1 | 1 | 1 | 1 | 12.5700 | 12.5700 | 100.0% | 100.0% | 0 | 0 | ±50.0 | OK |
| 2-Bromopyridine | Brc1ccccn1 | 4 | 4 | 4 | 20.7625 | 26.4067 | 100.0% | 100.0% | 0 | 0 | ±50.0 | OK |
| 2,6-Dichloropyridine | Clc1cccc(Cl)n1 | 5 | 5 | 4 | 20.1500 | 24.3815 | 80.0% | 80.0% | 1 | 1 | ±50.0 | OK |
| 4-Aminobenzoic acid | Nc1ccc(C(=O)O)cc1 | 10 | 10 | 9 | 18.3889 | 23.0095 | 90.0% | 90.0% | 1 | 1 | ±50.0 | OK |
| Ethyl 4-nitrobenzoate | CCOC(=O)c1ccc([N+](=O)[O-])cc1 | 11 | 11 | 11 | 20.9536 | 24.5985 | 100.0% | 100.0% | 0 | 0 | ±50.0 | OK |
| N,N-Dimethylacetamide | CN(C)C=O | 1 | 1 | 1 | 13.0300 | 13.0300 | 100.0% | 100.0% | 0 | 0 | ±50.0 | OK |
| 4-Methoxybenzoic acid | COc1ccc(C(=O)O)cc1 | 13 | 13 | 11 | 17.9700 | 20.6469 | 84.6% | 84.6% | 2 | 2 | ±50.0 | OK |
| 2-Methylpyridine | Cc1ccccn1 | 4 | 4 | 4 | 22.7850 | 24.9709 | 100.0% | 100.0% | 0 | 0 | ±50.0 | OK |
| 3,4-Dimethoxybenzaldehyde | COc1ccc(OC)c(C=O)c1 | 10 | 10 | 10 | 29.4650 | 32.5800 | 100.0% | 100.0% | 0 | 0 | ±50.0 | OK |
## Sheet: 1H NMR Validation
| 1H NMR Validation  |  [HEURISTIC] Predicted  vs  [EXPERIMENTAL] Reference |  |  |  |  |  |  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Compound | SMILES | Predicted Peaks [HEURISTIC] | Experimental Peaks [EXPERIMENTAL] | Matched | MAE | RMSE | Coverage [HEURISTIC] | Coverage [EXPERIMENTAL] | Missing (FN) | Extra (FP) | Tolerance | Status |
| Benzene | c1ccccc1 | 1 | 6 | 1 | 0.3700 | 0.3700 | 100.0% | 16.7% | 5 | 0 | ±0.5 | OK |
| Toluene | Cc1ccccc1 | 2 | 6 | 2 | 0.2900 | 0.2983 | 100.0% | 33.3% | 4 | 0 | ±0.5 | OK |
| Nitrobenzene | O=[N+]([O-])c1ccccc1 | 1 | 5 | 1 | 0.2400 | 0.2400 | 100.0% | 20.0% | 4 | 0 | ±0.5 | OK |
| Chlorobenzene | Clc1ccccc1 | 1 | 5 | 1 | 0.3700 | 0.3700 | 100.0% | 20.0% | 4 | 0 | ±0.5 | OK |
| Bromobenzene | Brc1ccccc1 | 1 | 5 | 1 | 0.0500 | 0.0500 | 100.0% | 20.0% | 4 | 0 | ±0.5 | OK |
| Fluorobenzene | Fc1ccccc1 | 1 | 5 | 1 | 0.3100 | 0.3100 | 100.0% | 20.0% | 4 | 0 | ±0.5 | OK |
| Iodobenzene | Ic1ccccc1 | 1 | 5 | 1 | 0.1900 | 0.1900 | 100.0% | 20.0% | 4 | 0 | ±0.5 | OK |
| Anisole | COc1ccccc1 | 2 | 6 | 2 | 0.1450 | 0.1551 | 100.0% | 33.3% | 4 | 0 | ±0.5 | OK |
| Ethyl acetate | CCOC(C)=O | 3 | 3 | 3 | 0.2733 | 0.2952 | 100.0% | 100.0% | 0 | 0 | ±0.5 | OK |
| Methyl benzoate | COC(=O)c1ccccc1 | 2 | 6 | 2 | 0.2550 | 0.2840 | 100.0% | 33.3% | 4 | 0 | ±0.5 | OK |
| Acetamide | CC(N)=O | 2 | 2 | 2 | 0.0800 | 0.0943 | 100.0% | 100.0% | 0 | 0 | ±0.5 | OK |
| Benzamide | NC(=O)c1ccccc1 | 2 | 6 | 2 | 0.3400 | 0.3640 | 100.0% | 33.3% | 4 | 0 | ±0.5 | OK |
| Pyridine | c1ccncc1 | 3 | 5 | 3 | 0.0367 | 0.0493 | 100.0% | 60.0% | 2 | 0 | ±0.5 | OK |
| Pyrrole | c1cc[nH]c1 | 2 | 5 | 2 | 0.0450 | 0.0515 | 100.0% | 40.0% | 3 | 0 | ±0.5 | OK |
| Furan | c1ccoc1 | 1 | 4 | 1 | 0.3700 | 0.3700 | 100.0% | 25.0% | 3 | 0 | ±0.5 | OK |
| Thiophene | c1ccsc1 | 1 | 4 | 1 | 0.4000 | 0.4000 | 100.0% | 25.0% | 3 | 0 | ±0.5 | OK |
| Indole | c1ccc2[nH]ccc2c1 | 5 | 7 | 5 | 0.1560 | 0.1767 | 100.0% | 71.4% | 2 | 0 | ±0.5 | OK |
| Quinoline | c1ccc2ncccc2c1 | 4 | 7 | 4 | 0.1825 | 0.2348 | 100.0% | 57.1% | 3 | 0 | ±0.5 | OK |
| Imidazole | c1c[nH]cn1 | 2 | 4 | 2 | 0.2000 | 0.2283 | 100.0% | 50.0% | 2 | 0 | ±0.5 | OK |
| Pyrimidine | c1cncnc1 | 2 | 4 | 2 | 0.1600 | 0.1603 | 100.0% | 50.0% | 2 | 0 | ±0.5 | OK |
| Purine | c1nc2[nH]cnc2[nH]1 | 2 | 4 | 2 | 0.0950 | 0.1275 | 100.0% | 50.0% | 2 | 0 | ±0.5 | OK |
| Benzoxazole | c1ccc2ocnc2c1 | 1 | 5 | 1 | 0.2800 | 0.2800 | 100.0% | 20.0% | 4 | 0 | ±0.5 | OK |
| Quinoxaline | c1ccc2c(c1)nc1ccccn12 | 3 | 8 | 3 | 0.3467 | 0.3667 | 100.0% | 37.5% | 5 | 0 | ±0.5 | OK |
| Ethanol | CCO | 3 | 3 | 3 | 0.1267 | 0.1378 | 100.0% | 100.0% | 0 | 0 | ±0.5 | OK |
| Ethyl methyl ether | CCOC | 3 | 3 | 3 | 0.2233 | 0.2322 | 100.0% | 100.0% | 0 | 0 | ±0.5 | OK |
| Diethyl ether | CCOCC | 2 | 4 | 2 | 0.0400 | 0.0412 | 100.0% | 50.0% | 2 | 0 | ±0.5 | OK |
| Methyl tert-butyl ether | COC(C)(C)C | 2 | 4 | 1 | 0.3900 | 0.3900 | 50.0% | 25.0% | 3 | 1 | ±0.5 | OK |
| Aspirin | CC(=O)Oc1ccccc1C(=O)O | 4 | 6 | 4 | 0.1750 | 0.1912 | 100.0% | 66.7% | 2 | 0 | ±0.5 | OK |
| Benzyl acetate | CC(=O)OCc1ccccc1 | 3 | 7 | 3 | 0.2633 | 0.2808 | 100.0% | 42.9% | 4 | 0 | ±0.5 | OK |
| N-Methylacetamide | CNC(C)=O | 3 | 3 | 3 | 0.3067 | 0.3348 | 100.0% | 100.0% | 0 | 0 | ±0.5 | OK |
| Nicotinamide | NC(=O)c1ccncc1 | 3 | 5 | 3 | 0.2067 | 0.2531 | 100.0% | 60.0% | 2 | 0 | ±0.5 | OK |
| Phenol | Oc1ccccc1 | 2 | 6 | 2 | 0.2100 | 0.2419 | 100.0% | 33.3% | 4 | 0 | ±0.5 | OK |
| Aniline | Nc1ccccc1 | 2 | 6 | 2 | 0.2350 | 0.2438 | 100.0% | 33.3% | 4 | 0 | ±0.5 | OK |
| Nitropropane | CCC[N+](=O)[O-] | 3 | 3 | 3 | 0.0967 | 0.1066 | 100.0% | 100.0% | 0 | 0 | ±0.5 | OK |
| 2-Chloropyridine | Clc1ccccn1 | 3 | 4 | 3 | 0.2067 | 0.2195 | 100.0% | 75.0% | 1 | 0 | ±0.5 | OK |
| 4-Nitrophenol | O=[N+]([O-])c1ccc(O)cc1 | 2 | 5 | 2 | 0.2850 | 0.3112 | 100.0% | 40.0% | 3 | 0 | ±0.5 | OK |
| 2-Chloroethylamine | NCCCl | 3 | 3 | 3 | 0.0633 | 0.0714 | 100.0% | 100.0% | 0 | 0 | ±0.5 | OK |
| 2-Bromoethanol | OCCBr | 3 | 3 | 3 | 0.2600 | 0.3191 | 100.0% | 100.0% | 0 | 0 | ±0.5 | OK |
| 4-Chloroanisole | COc1ccc(Cl)cc1 | 3 | 5 | 2 | 0.3650 | 0.3798 | 66.7% | 40.0% | 3 | 1 | ±0.5 | OK |
| 1,4-Dioxane | C1COCCO1 | 1 | 4 | 1 | 0.3300 | 0.3300 | 100.0% | 25.0% | 3 | 0 | ±0.5 | OK |
| 1,3,5-Triazine | c1ncncn1 | 1 | 3 | 1 | 0.1900 | 0.1900 | 100.0% | 33.3% | 2 | 0 | ±0.5 | OK |
| Benzimidazole | c1ccc2[nH]cnc2c1 | 4 | 6 | 4 | 0.1875 | 0.2454 | 100.0% | 66.7% | 2 | 0 | ±0.5 | OK |
| Coumarin | O=C1CC=Cc2ccccc2O1 | 3 | 7 | 3 | 0.0567 | 0.0592 | 100.0% | 42.9% | 4 | 0 | ±0.5 | OK |
| Naphthalene | c1ccc2ccccc2c1 | 1 | 8 | 1 | 0.2300 | 0.2300 | 100.0% | 12.5% | 7 | 0 | ±0.5 | OK |
| Phenanthrene | c1ccc2cc3ccccc3cc2c1 | 1 | 10 | 1 | 0.1700 | 0.1700 | 100.0% | 10.0% | 9 | 0 | ±0.5 | OK |
| Indene | C1=Cc2ccccc2C1 | 3 | 7 | 3 | 0.0700 | 0.0759 | 100.0% | 42.9% | 4 | 0 | ±0.5 | OK |
| Quinazoline | c1ccc2nccc-2nc1 | 2 | 6 | 2 | 0.2950 | 0.3021 | 100.0% | 33.3% | 4 | 0 | ±0.5 | OK |
| Isoquinoline | c1ccc2cnccc2c1 | 4 | 7 | 4 | 0.1300 | 0.1632 | 100.0% | 57.1% | 3 | 0 | ±0.5 | OK |
| 1,4-Dimethoxybenzene | COc1ccc(OC)cc1 | 2 | 6 | 2 | 0.0650 | 0.0738 | 100.0% | 33.3% | 4 | 0 | ±0.5 | OK |
| Cyclohexanone | O=C1CCCCC1 | 2 | 5 | 2 | 0.2100 | 0.2470 | 100.0% | 40.0% | 3 | 0 | ±0.5 | OK |
| 2,4,6-Trinitrotoluene | Cc1c([N+](=O)[O-])cc([N+](=O)[O-])cc1[N+](=O)[O-] | 2 | 3 | 2 | 0.1800 | 0.1825 | 100.0% | 66.7% | 1 | 0 | ±0.5 | OK |
| 4-Vinylpyridine | C=Cc1ccncc1 | 3 | 6 | 3 | 0.2633 | 0.3022 | 100.0% | 50.0% | 3 | 0 | ±0.5 | OK |
| 2-Methylfuran | Cc1ccoc1 | 2 | 4 | 2 | 0.3400 | 0.3437 | 100.0% | 50.0% | 2 | 0 | ±0.5 | OK |
| 2-Bromopyridine | Brc1ccccn1 | 3 | 4 | 3 | 0.2167 | 0.2437 | 100.0% | 75.0% | 1 | 0 | ±0.5 | OK |
| 2,6-Dichloropyridine | Clc1cccc(Cl)n1 | 2 | 3 | 2 | 0.1900 | 0.1900 | 100.0% | 66.7% | 1 | 0 | ±0.5 | OK |
| 4-Aminobenzoic acid | Nc1ccc(C(=O)O)cc1 | 4 | 6 | 4 | 0.1775 | 0.1805 | 100.0% | 66.7% | 2 | 0 | ±0.5 | OK |
| Ethyl 4-nitrobenzoate | CCOC(=O)c1ccc([N+](=O)[O-])cc1 | 4 | 6 | 4 | 0.3150 | 0.3520 | 100.0% | 66.7% | 2 | 0 | ±0.5 | OK |
| N,N-Dimethylacetamide | CN(C)C=O | 2 | 3 | 2 | 0.2400 | 0.2500 | 100.0% | 66.7% | 1 | 0 | ±0.5 | OK |
| 4-Methoxybenzoic acid | COc1ccc(C(=O)O)cc1 | 4 | 6 | 4 | 0.0700 | 0.0745 | 100.0% | 66.7% | 2 | 0 | ±0.5 | OK |
| 2-Methylpyridine | Cc1ccccn1 | 4 | 5 | 3 | 0.2267 | 0.2285 | 75.0% | 60.0% | 2 | 1 | ±0.5 | OK |
| 3,4-Dimethoxybenzaldehyde | COc1ccc(OC)c(C=O)c1 | 3 | 6 | 3 | 0.2467 | 0.2862 | 100.0% | 50.0% | 3 | 0 | ±0.5 | OK |
## Sheet: 13C NMR Validation
| 13C NMR Validation  |  [HEURISTIC] Predicted  vs  [EXPERIMENTAL] Reference |  |  |  |  |  |  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Compound | SMILES | Predicted Peaks [HEURISTIC] | Experimental Peaks [EXPERIMENTAL] | Matched | MAE | RMSE | Coverage [HEURISTIC] | Coverage [EXPERIMENTAL] | Missing (FN) | Extra (FP) | Tolerance | Status |
| Benzene | c1ccccc1 | 1 | 6 | 1 | 2.2100 | 2.2100 | 100.0% | 16.7% | 5 | 0 | ±5.0 | OK |
| Toluene | Cc1ccccc1 | 3 | 7 | 3 | 2.8667 | 3.2805 | 100.0% | 42.9% | 4 | 0 | ±5.0 | OK |
| Nitrobenzene | O=[N+]([O-])c1ccccc1 | 2 | 6 | 2 | 0.4400 | 0.4512 | 100.0% | 33.3% | 4 | 0 | ±5.0 | OK |
| Chlorobenzene | Clc1ccccc1 | 3 | 6 | 3 | 3.7733 | 3.8382 | 100.0% | 50.0% | 3 | 0 | ±5.0 | OK |
| Bromobenzene | Brc1ccccc1 | 3 | 6 | 3 | 2.8500 | 3.0166 | 100.0% | 50.0% | 3 | 0 | ±5.0 | OK |
| Fluorobenzene | Fc1ccccc1 | 3 | 6 | 3 | 0.3533 | 0.4859 | 100.0% | 50.0% | 3 | 0 | ±5.0 | OK |
| Iodobenzene | Ic1ccccc1 | 3 | 6 | 3 | 1.6900 | 2.2292 | 100.0% | 50.0% | 3 | 0 | ±5.0 | OK |
| Anisole | COc1ccccc1 | 3 | 7 | 2 | 1.7050 | 2.2157 | 66.7% | 28.6% | 5 | 1 | ±5.0 | OK |
| Ethyl acetate | CCOC(C)=O | 4 | 4 | 4 | 2.1150 | 2.6551 | 100.0% | 100.0% | 0 | 0 | ±5.0 | OK |
| Methyl benzoate | COC(=O)c1ccccc1 | 5 | 8 | 5 | 1.6320 | 1.9682 | 100.0% | 62.5% | 3 | 0 | ±5.0 | OK |
| Acetamide | CC(N)=O | 2 | 2 | 2 | 2.5650 | 2.7622 | 100.0% | 100.0% | 0 | 0 | ±5.0 | OK |
| Benzamide | NC(=O)c1ccccc1 | 4 | 7 | 4 | 1.7250 | 1.7442 | 100.0% | 57.1% | 3 | 0 | ±5.0 | OK |
| Pyridine | c1ccncc1 | 3 | 5 | 3 | 2.8300 | 2.8884 | 100.0% | 60.0% | 2 | 0 | ±5.0 | OK |
| Pyrrole | c1cc[nH]c1 | 2 | 4 | 2 | 1.7600 | 2.1645 | 100.0% | 50.0% | 2 | 0 | ±5.0 | OK |
| Furan | c1ccoc1 | 2 | 4 | 2 | 1.0950 | 1.1422 | 100.0% | 50.0% | 2 | 0 | ±5.0 | OK |
| Thiophene | c1ccsc1 | 2 | 4 | 2 | 2.1500 | 2.9638 | 100.0% | 50.0% | 2 | 0 | ±5.0 | OK |
| Indole | c1ccc2[nH]ccc2c1 | 7 | 8 | 7 | 2.4714 | 2.9804 | 100.0% | 87.5% | 1 | 0 | ±5.0 | OK |
| Quinoline | c1ccc2ncccc2c1 | 6 | 9 | 6 | 3.4317 | 3.7246 | 100.0% | 66.7% | 3 | 0 | ±5.0 | OK |
| Imidazole | c1c[nH]cn1 | 2 | 3 | 2 | 1.0500 | 1.0517 | 100.0% | 66.7% | 1 | 0 | ±5.0 | OK |
| Pyrimidine | c1cncnc1 | 3 | 4 | 3 | 0.7700 | 0.8107 | 100.0% | 75.0% | 1 | 0 | ±5.0 | OK |
| Purine | c1nc2[nH]cnc2[nH]1 | 2 | 4 | 2 | 2.7800 | 2.9578 | 100.0% | 50.0% | 2 | 0 | ±5.0 | OK |
| Benzoxazole | c1ccc2ocnc2c1 | 4 | 7 | 4 | 1.7250 | 1.7979 | 100.0% | 57.1% | 3 | 0 | ±5.0 | OK |
| Quinoxaline | c1ccc2c(c1)nc1ccccn12 | 5 | 11 | 5 | 2.6700 | 2.8625 | 100.0% | 45.5% | 6 | 0 | ±5.0 | OK |
| Ethanol | CCO | 2 | 2 | 2 | 1.5600 | 2.0116 | 100.0% | 100.0% | 0 | 0 | ±5.0 | OK |
| Ethyl methyl ether | CCOC | 3 | 3 | 3 | 0.7900 | 0.8945 | 100.0% | 100.0% | 0 | 0 | ±5.0 | OK |
| Diethyl ether | CCOCC | 2 | 4 | 2 | 2.8850 | 2.8857 | 100.0% | 50.0% | 2 | 0 | ±5.0 | OK |
| Methyl tert-butyl ether | COC(C)(C)C | 3 | 5 | 3 | 2.0267 | 2.7042 | 100.0% | 60.0% | 2 | 0 | ±5.0 | OK |
| Aspirin | CC(=O)Oc1ccccc1C(=O)O | 7 | 9 | 7 | 2.1329 | 2.4010 | 100.0% | 77.8% | 2 | 0 | ±5.0 | OK |
| Benzyl acetate | CC(=O)OCc1ccccc1 | 5 | 9 | 5 | 1.5860 | 2.0212 | 100.0% | 55.6% | 4 | 0 | ±5.0 | OK |
| N-Methylacetamide | CNC(C)=O | 3 | 3 | 1 | 4.1500 | 4.1500 | 33.3% | 33.3% | 2 | 2 | ±5.0 | OK |
| Nicotinamide | NC(=O)c1ccncc1 | 4 | 6 | 4 | 2.0125 | 2.6288 | 100.0% | 66.7% | 2 | 0 | ±5.0 | OK |
| Phenol | Oc1ccccc1 | 2 | 6 | 2 | 3.1150 | 3.2124 | 100.0% | 33.3% | 4 | 0 | ±5.0 | OK |
| Aniline | Nc1ccccc1 | 2 | 6 | 2 | 1.5300 | 1.7551 | 100.0% | 33.3% | 4 | 0 | ±5.0 | OK |
| Nitropropane | CCC[N+](=O)[O-] | 3 | 3 | 3 | 2.3900 | 2.7899 | 100.0% | 100.0% | 0 | 0 | ±5.0 | OK |
| 2-Chloropyridine | Clc1ccccn1 | 5 | 5 | 4 | 1.3550 | 1.8395 | 80.0% | 80.0% | 1 | 1 | ±5.0 | OK |
| 4-Nitrophenol | O=[N+]([O-])c1ccc(O)cc1 | 3 | 6 | 3 | 2.3600 | 2.5203 | 100.0% | 50.0% | 3 | 0 | ±5.0 | OK |
| 2-Chloroethylamine | NCCCl | 2 | 2 | 2 | 2.7300 | 2.9781 | 100.0% | 100.0% | 0 | 0 | ±5.0 | OK |
| 2-Bromoethanol | OCCBr | 2 | 2 | 2 | 1.9300 | 2.0430 | 100.0% | 100.0% | 0 | 0 | ±5.0 | OK |
| 4-Chloroanisole | COc1ccc(Cl)cc1 | 5 | 7 | 4 | 2.2975 | 2.8347 | 80.0% | 57.1% | 3 | 1 | ±5.0 | OK |
| 1,4-Dioxane | C1COCCO1 | 1 | 4 | 1 | 1.5300 | 1.5300 | 100.0% | 25.0% | 3 | 0 | ±5.0 | OK |
| 1,3,5-Triazine | c1ncncn1 | 1 | 3 | 1 | 2.4500 | 2.4500 | 100.0% | 33.3% | 2 | 0 | ±5.0 | OK |
| Benzimidazole | c1ccc2[nH]cnc2c1 | 4 | 7 | 4 | 2.3625 | 2.5543 | 100.0% | 57.1% | 3 | 0 | ±5.0 | OK |
| Coumarin | O=C1CC=Cc2ccccc2O1 | 6 | 10 | 6 | 2.1767 | 2.4329 | 100.0% | 60.0% | 4 | 0 | ±5.0 | OK |
| Naphthalene | c1ccc2ccccc2c1 | 2 | 10 | 2 | 2.0700 | 2.8853 | 100.0% | 20.0% | 8 | 0 | ±5.0 | OK |
| Phenanthrene | c1ccc2cc3ccccc3cc2c1 | 2 | 14 | 2 | 3.6200 | 3.6491 | 100.0% | 14.3% | 12 | 0 | ±5.0 | OK |
| Indene | C1=Cc2ccccc2C1 | 4 | 9 | 4 | 2.5825 | 2.7529 | 100.0% | 44.4% | 5 | 0 | ±5.0 | OK |
| Quinazoline | c1ccc2nccc-2nc1 | 5 | 8 | 5 | 2.6340 | 2.8296 | 100.0% | 62.5% | 3 | 0 | ±5.0 | OK |
| Isoquinoline | c1ccc2cnccc2c1 | 6 | 9 | 6 | 3.2117 | 3.3923 | 100.0% | 66.7% | 3 | 0 | ±5.0 | OK |
| 1,4-Dimethoxybenzene | COc1ccc(OC)cc1 | 3 | 8 | 3 | 1.9300 | 2.2413 | 100.0% | 37.5% | 5 | 0 | ±5.0 | OK |
| Cyclohexanone | O=C1CCCCC1 | 3 | 6 | 2 | 0.5700 | 0.6441 | 66.7% | 33.3% | 4 | 1 | ±5.0 | OK |
| 2,4,6-Trinitrotoluene | Cc1c([N+](=O)[O-])cc([N+](=O)[O-])cc1[N+](=O)[O-] | 4 | 7 | 4 | 1.9200 | 2.5822 | 100.0% | 57.1% | 3 | 0 | ±5.0 | OK |
| 4-Vinylpyridine | C=Cc1ccncc1 | 5 | 7 | 4 | 2.3875 | 2.8341 | 80.0% | 57.1% | 3 | 1 | ±5.0 | OK |
| 2-Methylfuran | Cc1ccoc1 | 4 | 5 | 4 | 2.8050 | 3.1607 | 100.0% | 80.0% | 1 | 0 | ±5.0 | OK |
| 2-Bromopyridine | Brc1ccccn1 | 5 | 5 | 5 | 2.7440 | 2.7874 | 100.0% | 100.0% | 0 | 0 | ±5.0 | OK |
| 2,6-Dichloropyridine | Clc1cccc(Cl)n1 | 3 | 5 | 3 | 2.3433 | 2.9467 | 100.0% | 60.0% | 2 | 0 | ±5.0 | OK |
| 4-Aminobenzoic acid | Nc1ccc(C(=O)O)cc1 | 5 | 7 | 5 | 3.0560 | 3.1545 | 100.0% | 71.4% | 2 | 0 | ±5.0 | OK |
| Ethyl 4-nitrobenzoate | CCOC(=O)c1ccc([N+](=O)[O-])cc1 | 7 | 9 | 7 | 3.7043 | 3.8607 | 100.0% | 77.8% | 2 | 0 | ±5.0 | OK |
| N,N-Dimethylacetamide | CN(C)C=O | 2 | 3 | 2 | 0.7650 | 0.9879 | 100.0% | 66.7% | 1 | 0 | ±5.0 | OK |
| 4-Methoxybenzoic acid | COc1ccc(C(=O)O)cc1 | 6 | 8 | 4 | 0.8125 | 0.9190 | 66.7% | 50.0% | 4 | 2 | ±5.0 | OK |
| 2-Methylpyridine | Cc1ccccn1 | 5 | 6 | 5 | 2.3080 | 2.7900 | 100.0% | 83.3% | 1 | 0 | ±5.0 | OK |
| 3,4-Dimethoxybenzaldehyde | COc1ccc(OC)c(C=O)c1 | 6 | 9 | 6 | 1.7017 | 1.9135 | 100.0% | 66.7% | 3 | 0 | ±5.0 | OK |
## Sheet: Per-Molecule Detail
| Per-Molecule Summary  |  [HEURISTIC] vs [EXPERIMENTAL]  |  All Three Domains |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Molecule | SMILES | Success | IR Pred | IR Exp | IR Match | IR MAE | IR RMSE | IR Cov% | 1H NMR Pred | 1H NMR Exp | 1H NMR Match | 1H NMR MAE | 1H NMR RMSE | 1H NMR Cov% | 13C NMR Pred | 13C NMR Exp | 13C NMR Match | 13C NMR MAE | 13C NMR RMSE | 13C NMR Cov% |
| Benzene | c1ccccc1 | OK | 3 | 3 | 3 | 3.567 | 3.622 | 100.0% | 1 | 6 | 1 | 0.370 | 0.370 | 16.7% | 1 | 6 | 1 | 2.210 | 2.210 | 16.7% |
| Toluene | Cc1ccccc1 | OK | 4 | 4 | 4 | 16.337 | 20.959 | 100.0% | 2 | 6 | 2 | 0.290 | 0.298 | 33.3% | 3 | 7 | 3 | 2.867 | 3.281 | 42.9% |
| Nitrobenzene | O=[N+]([O-])c1ccccc1 | OK | 5 | 5 | 4 | 19.145 | 19.430 | 80.0% | 1 | 5 | 1 | 0.240 | 0.240 | 20.0% | 2 | 6 | 2 | 0.440 | 0.451 | 33.3% |
| Chlorobenzene | Clc1ccccc1 | OK | 4 | 4 | 4 | 14.457 | 14.670 | 100.0% | 1 | 5 | 1 | 0.370 | 0.370 | 20.0% | 3 | 6 | 3 | 3.773 | 3.838 | 50.0% |
| Bromobenzene | Brc1ccccc1 | OK | 4 | 4 | 4 | 18.513 | 22.625 | 100.0% | 1 | 5 | 1 | 0.050 | 0.050 | 20.0% | 3 | 6 | 3 | 2.850 | 3.017 | 50.0% |
| Fluorobenzene | Fc1ccccc1 | OK | 4 | 4 | 4 | 11.480 | 13.556 | 100.0% | 1 | 5 | 1 | 0.310 | 0.310 | 20.0% | 3 | 6 | 3 | 0.353 | 0.486 | 50.0% |
| Iodobenzene | Ic1ccccc1 | OK | 4 | 4 | 4 | 22.012 | 23.345 | 100.0% | 1 | 5 | 1 | 0.190 | 0.190 | 20.0% | 3 | 6 | 3 | 1.690 | 2.229 | 50.0% |
| Anisole | COc1ccccc1 | OK | 6 | 6 | 5 | 12.232 | 13.740 | 83.3% | 2 | 6 | 2 | 0.145 | 0.155 | 33.3% | 3 | 7 | 2 | 1.705 | 2.216 | 28.6% |
| Ethyl acetate | CCOC(C)=O | OK | 6 | 6 | 6 | 21.418 | 26.631 | 100.0% | 3 | 3 | 3 | 0.273 | 0.295 | 100.0% | 4 | 4 | 4 | 2.115 | 2.655 | 100.0% |
| Methyl benzoate | COC(=O)c1ccccc1 | OK | 9 | 9 | 8 | 14.978 | 19.356 | 88.9% | 2 | 6 | 2 | 0.255 | 0.284 | 33.3% | 5 | 8 | 5 | 1.632 | 1.968 | 62.5% |
| Acetamide | CC(N)=O | OK | 5 | 5 | 4 | 13.340 | 19.196 | 80.0% | 2 | 2 | 2 | 0.080 | 0.094 | 100.0% | 2 | 2 | 2 | 2.565 | 2.762 | 100.0% |
| Benzamide | NC(=O)c1ccccc1 | OK | 7 | 7 | 7 | 19.061 | 22.381 | 100.0% | 2 | 6 | 2 | 0.340 | 0.364 | 33.3% | 4 | 7 | 4 | 1.725 | 1.744 | 57.1% |
| Pyridine | c1ccncc1 | OK | 3 | 3 | 2 | 23.315 | 32.923 | 66.7% | 3 | 5 | 3 | 0.037 | 0.049 | 60.0% | 3 | 5 | 3 | 2.830 | 2.888 | 60.0% |
| Pyrrole | c1cc[nH]c1 | OK | 0 | 0 | 0 | N/A | N/A | 0.0% | 2 | 5 | 2 | 0.045 | 0.051 | 40.0% | 2 | 4 | 2 | 1.760 | 2.165 | 50.0% |
| Furan | c1ccoc1 | OK | 0 | 0 | 0 | N/A | N/A | 0.0% | 1 | 4 | 1 | 0.370 | 0.370 | 25.0% | 2 | 4 | 2 | 1.095 | 1.142 | 50.0% |
| Thiophene | c1ccsc1 | OK | 0 | 0 | 0 | N/A | N/A | 0.0% | 1 | 4 | 1 | 0.400 | 0.400 | 25.0% | 2 | 4 | 2 | 2.150 | 2.964 | 50.0% |
| Indole | c1ccc2[nH]ccc2c1 | OK | 3 | 3 | 3 | 17.593 | 20.154 | 100.0% | 5 | 7 | 5 | 0.156 | 0.177 | 71.4% | 7 | 8 | 7 | 2.471 | 2.980 | 87.5% |
| Quinoline | c1ccc2ncccc2c1 | OK | 6 | 6 | 6 | 20.112 | 22.190 | 100.0% | 4 | 7 | 4 | 0.183 | 0.235 | 57.1% | 6 | 9 | 6 | 3.432 | 3.725 | 66.7% |
| Imidazole | c1c[nH]cn1 | OK | 0 | 0 | 0 | N/A | N/A | 0.0% | 2 | 4 | 2 | 0.200 | 0.228 | 50.0% | 2 | 3 | 2 | 1.050 | 1.052 | 66.7% |
| Pyrimidine | c1cncnc1 | OK | 3 | 3 | 3 | 19.423 | 22.740 | 100.0% | 2 | 4 | 2 | 0.160 | 0.160 | 50.0% | 3 | 4 | 3 | 0.770 | 0.811 | 75.0% |
| Purine | c1nc2[nH]cnc2[nH]1 | OK | 0 | 0 | 0 | N/A | N/A | 0.0% | 2 | 4 | 2 | 0.095 | 0.127 | 50.0% | 2 | 4 | 2 | 2.780 | 2.958 | 50.0% |
| Benzoxazole | c1ccc2ocnc2c1 | OK | 3 | 3 | 3 | 16.927 | 26.703 | 100.0% | 1 | 5 | 1 | 0.280 | 0.280 | 20.0% | 4 | 7 | 4 | 1.725 | 1.798 | 57.1% |
| Quinoxaline | c1ccc2c(c1)nc1ccccn12 | OK | 6 | 6 | 5 | 12.116 | 15.318 | 83.3% | 3 | 8 | 3 | 0.347 | 0.367 | 37.5% | 5 | 11 | 5 | 2.670 | 2.863 | 45.5% |
| Ethanol | CCO | OK | 4 | 4 | 4 | 19.807 | 25.371 | 100.0% | 3 | 3 | 3 | 0.127 | 0.138 | 100.0% | 2 | 2 | 2 | 1.560 | 2.012 | 100.0% |
| Ethyl methyl ether | CCOC | OK | 3 | 3 | 3 | 22.673 | 27.985 | 100.0% | 3 | 3 | 3 | 0.223 | 0.232 | 100.0% | 3 | 3 | 3 | 0.790 | 0.895 | 100.0% |
| Diethyl ether | CCOCC | OK | 3 | 3 | 3 | 12.470 | 14.268 | 100.0% | 2 | 4 | 2 | 0.040 | 0.041 | 50.0% | 2 | 4 | 2 | 2.885 | 2.886 | 50.0% |
| Methyl tert-butyl ether | COC(C)(C)C | OK | 3 | 3 | 3 | 20.687 | 25.886 | 100.0% | 2 | 4 | 1 | 0.390 | 0.390 | 25.0% | 3 | 5 | 3 | 2.027 | 2.704 | 60.0% |
| Aspirin | CC(=O)Oc1ccccc1C(=O)O | OK | 16 | 16 | 16 | 16.231 | 18.431 | 100.0% | 4 | 6 | 4 | 0.175 | 0.191 | 66.7% | 7 | 9 | 7 | 2.133 | 2.401 | 77.8% |
| Benzyl acetate | CC(=O)OCc1ccccc1 | OK | 9 | 9 | 9 | 9.387 | 11.447 | 100.0% | 3 | 7 | 3 | 0.263 | 0.281 | 42.9% | 5 | 9 | 5 | 1.586 | 2.021 | 55.6% |
| N-Methylacetamide | CNC(C)=O | OK | 5 | 5 | 4 | 14.415 | 24.604 | 80.0% | 3 | 3 | 3 | 0.307 | 0.335 | 100.0% | 3 | 3 | 1 | 4.150 | 4.150 | 33.3% |
| Nicotinamide | NC(=O)c1ccncc1 | OK | 7 | 7 | 7 | 22.711 | 24.324 | 100.0% | 3 | 5 | 3 | 0.207 | 0.253 | 60.0% | 4 | 6 | 4 | 2.013 | 2.629 | 66.7% |
| Phenol | Oc1ccccc1 | OK | 9 | 9 | 9 | 13.493 | 17.994 | 100.0% | 2 | 6 | 2 | 0.210 | 0.242 | 33.3% | 2 | 6 | 2 | 3.115 | 3.212 | 33.3% |
| Aniline | Nc1ccccc1 | OK | 3 | 3 | 3 | 40.110 | 40.663 | 100.0% | 2 | 6 | 2 | 0.235 | 0.244 | 33.3% | 2 | 6 | 2 | 1.530 | 1.755 | 33.3% |
| Nitropropane | CCC[N+](=O)[O-] | OK | 3 | 3 | 3 | 6.550 | 7.923 | 100.0% | 3 | 3 | 3 | 0.097 | 0.107 | 100.0% | 3 | 3 | 3 | 2.390 | 2.790 | 100.0% |
| 2-Chloropyridine | Clc1ccccn1 | OK | 4 | 4 | 4 | 14.260 | 16.300 | 100.0% | 3 | 4 | 3 | 0.207 | 0.220 | 75.0% | 5 | 5 | 4 | 1.355 | 1.839 | 80.0% |
| 4-Nitrophenol | O=[N+]([O-])c1ccc(O)cc1 | OK | 11 | 11 | 11 | 13.955 | 17.945 | 100.0% | 2 | 5 | 2 | 0.285 | 0.311 | 40.0% | 3 | 6 | 3 | 2.360 | 2.520 | 50.0% |
| 2-Chloroethylamine | NCCCl | OK | 5 | 5 | 5 | 16.270 | 20.177 | 100.0% | 3 | 3 | 3 | 0.063 | 0.071 | 100.0% | 2 | 2 | 2 | 2.730 | 2.978 | 100.0% |
| 2-Bromoethanol | OCCBr | OK | 5 | 5 | 4 | 26.878 | 27.374 | 80.0% | 3 | 3 | 3 | 0.260 | 0.319 | 100.0% | 2 | 2 | 2 | 1.930 | 2.043 | 100.0% |
| 4-Chloroanisole | COc1ccc(Cl)cc1 | OK | 7 | 7 | 6 | 26.447 | 29.362 | 85.7% | 3 | 5 | 2 | 0.365 | 0.380 | 40.0% | 5 | 7 | 4 | 2.297 | 2.835 | 57.1% |
| 1,4-Dioxane | C1COCCO1 | OK | 5 | 5 | 5 | 17.882 | 23.736 | 100.0% | 1 | 4 | 1 | 0.330 | 0.330 | 25.0% | 1 | 4 | 1 | 1.530 | 1.530 | 25.0% |
| 1,3,5-Triazine | c1ncncn1 | OK | 3 | 3 | 3 | 25.733 | 29.948 | 100.0% | 1 | 3 | 1 | 0.190 | 0.190 | 33.3% | 1 | 3 | 1 | 2.450 | 2.450 | 33.3% |
| Benzimidazole | c1ccc2[nH]cnc2c1 | OK | 3 | 3 | 3 | 16.563 | 20.868 | 100.0% | 4 | 6 | 4 | 0.187 | 0.245 | 66.7% | 4 | 7 | 4 | 2.362 | 2.554 | 57.1% |
| Coumarin | O=C1CC=Cc2ccccc2O1 | OK | 12 | 12 | 12 | 16.322 | 21.022 | 100.0% | 3 | 7 | 3 | 0.057 | 0.059 | 42.9% | 6 | 10 | 6 | 2.177 | 2.433 | 60.0% |
| Naphthalene | c1ccc2ccccc2c1 | OK | 6 | 6 | 6 | 13.192 | 16.346 | 100.0% | 1 | 8 | 1 | 0.230 | 0.230 | 12.5% | 2 | 10 | 2 | 2.070 | 2.885 | 20.0% |
| Phenanthrene | c1ccc2cc3ccccc3cc2c1 | OK | 9 | 9 | 8 | 12.976 | 15.820 | 88.9% | 1 | 10 | 1 | 0.170 | 0.170 | 10.0% | 2 | 14 | 2 | 3.620 | 3.649 | 14.3% |
| Indene | C1=Cc2ccccc2C1 | OK | 7 | 7 | 7 | 16.753 | 20.925 | 100.0% | 3 | 7 | 3 | 0.070 | 0.076 | 42.9% | 4 | 9 | 4 | 2.582 | 2.753 | 44.4% |
| Quinazoline | c1ccc2nccc-2nc1 | OK | 0 | 0 | 0 | N/A | N/A | 0.0% | 2 | 6 | 2 | 0.295 | 0.302 | 33.3% | 5 | 8 | 5 | 2.634 | 2.830 | 62.5% |
| Isoquinoline | c1ccc2cnccc2c1 | OK | 6 | 6 | 5 | 21.586 | 23.162 | 83.3% | 4 | 7 | 4 | 0.130 | 0.163 | 57.1% | 6 | 9 | 6 | 3.212 | 3.392 | 66.7% |
| 1,4-Dimethoxybenzene | COc1ccc(OC)cc1 | OK | 8 | 8 | 7 | 27.000 | 30.857 | 87.5% | 2 | 6 | 2 | 0.065 | 0.074 | 33.3% | 3 | 8 | 3 | 1.930 | 2.241 | 37.5% |
| Cyclohexanone | O=C1CCCCC1 | OK | 3 | 3 | 3 | 14.727 | 17.256 | 100.0% | 2 | 5 | 2 | 0.210 | 0.247 | 40.0% | 3 | 6 | 2 | 0.570 | 0.644 | 33.3% |
| 2,4,6-Trinitrotoluene | Cc1c([N+](=O)[O-])cc([N+](=O)[O-])cc1[N+](=O)[O-] | OK | 10 | 10 | 9 | 17.274 | 22.242 | 90.0% | 2 | 3 | 2 | 0.180 | 0.182 | 66.7% | 4 | 7 | 4 | 1.920 | 2.582 | 57.1% |
| 4-Vinylpyridine | C=Cc1ccncc1 | OK | 6 | 6 | 6 | 21.390 | 24.540 | 100.0% | 3 | 6 | 3 | 0.263 | 0.302 | 50.0% | 5 | 7 | 4 | 2.387 | 2.834 | 57.1% |
| 2-Methylfuran | Cc1ccoc1 | OK | 1 | 1 | 1 | 12.570 | 12.570 | 100.0% | 2 | 4 | 2 | 0.340 | 0.344 | 50.0% | 4 | 5 | 4 | 2.805 | 3.161 | 80.0% |
| 2-Bromopyridine | Brc1ccccn1 | OK | 4 | 4 | 4 | 20.762 | 26.407 | 100.0% | 3 | 4 | 3 | 0.217 | 0.244 | 75.0% | 5 | 5 | 5 | 2.744 | 2.787 | 100.0% |
| 2,6-Dichloropyridine | Clc1cccc(Cl)n1 | OK | 5 | 5 | 4 | 20.150 | 24.382 | 80.0% | 2 | 3 | 2 | 0.190 | 0.190 | 66.7% | 3 | 5 | 3 | 2.343 | 2.947 | 60.0% |
| 4-Aminobenzoic acid | Nc1ccc(C(=O)O)cc1 | OK | 10 | 10 | 9 | 18.389 | 23.009 | 90.0% | 4 | 6 | 4 | 0.178 | 0.180 | 66.7% | 5 | 7 | 5 | 3.056 | 3.155 | 71.4% |
| Ethyl 4-nitrobenzoate | CCOC(=O)c1ccc([N+](=O)[O-])cc1 | OK | 11 | 11 | 11 | 20.954 | 24.598 | 100.0% | 4 | 6 | 4 | 0.315 | 0.352 | 66.7% | 7 | 9 | 7 | 3.704 | 3.861 | 77.8% |
| N,N-Dimethylacetamide | CN(C)C=O | OK | 1 | 1 | 1 | 13.030 | 13.030 | 100.0% | 2 | 3 | 2 | 0.240 | 0.250 | 66.7% | 2 | 3 | 2 | 0.765 | 0.988 | 66.7% |
| 4-Methoxybenzoic acid | COc1ccc(C(=O)O)cc1 | OK | 13 | 13 | 11 | 17.970 | 20.647 | 84.6% | 4 | 6 | 4 | 0.070 | 0.074 | 66.7% | 6 | 8 | 4 | 0.813 | 0.919 | 50.0% |
| 2-Methylpyridine | Cc1ccccn1 | OK | 4 | 4 | 4 | 22.785 | 24.971 | 100.0% | 4 | 5 | 3 | 0.227 | 0.228 | 60.0% | 5 | 6 | 5 | 2.308 | 2.790 | 83.3% |
| 3,4-Dimethoxybenzaldehyde | COc1ccc(OC)c(C=O)c1 | OK | 10 | 10 | 10 | 29.465 | 32.580 | 100.0% | 3 | 6 | 3 | 0.247 | 0.286 | 50.0% | 6 | 9 | 6 | 1.702 | 1.913 | 66.7% |
## Sheet: Missing Predictions
| Missing Predictions (False Negatives)  |  [EXPERIMENTAL] peaks with no [HEURISTIC] match |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Molecule | Domain | Experimental Value [EXPERIMENTAL] | Nearest Predicted [HEURISTIC] | Gap | Tolerance Used |
| Benzene | 1H NMR | 5 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| Benzene | 13C NMR | 5 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| Toluene | 1H NMR | 4 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| Toluene | 13C NMR | 4 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| Nitrobenzene | IR | 1 peak(s) unmatched | 1 extra predicted | - | ±50.0 |
| Nitrobenzene | 1H NMR | 4 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| Nitrobenzene | 13C NMR | 4 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| Chlorobenzene | 1H NMR | 4 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| Chlorobenzene | 13C NMR | 3 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| Bromobenzene | 1H NMR | 4 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| Bromobenzene | 13C NMR | 3 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| Fluorobenzene | 1H NMR | 4 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| Fluorobenzene | 13C NMR | 3 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| Iodobenzene | 1H NMR | 4 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| Iodobenzene | 13C NMR | 3 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| Anisole | IR | 1 peak(s) unmatched | 1 extra predicted | - | ±50.0 |
| Anisole | 1H NMR | 4 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| Anisole | 13C NMR | 5 peak(s) unmatched | 1 extra predicted | - | ±5.0 |
| Methyl benzoate | IR | 1 peak(s) unmatched | 1 extra predicted | - | ±50.0 |
| Methyl benzoate | 1H NMR | 4 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| Methyl benzoate | 13C NMR | 3 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| Acetamide | IR | 1 peak(s) unmatched | 1 extra predicted | - | ±50.0 |
| Benzamide | 1H NMR | 4 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| Benzamide | 13C NMR | 3 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| Pyridine | IR | 1 peak(s) unmatched | 1 extra predicted | - | ±50.0 |
| Pyridine | 1H NMR | 2 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| Pyridine | 13C NMR | 2 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| Pyrrole | 1H NMR | 3 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| Pyrrole | 13C NMR | 2 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| Furan | 1H NMR | 3 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| Furan | 13C NMR | 2 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| Thiophene | 1H NMR | 3 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| Thiophene | 13C NMR | 2 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| Indole | 1H NMR | 2 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| Indole | 13C NMR | 1 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| Quinoline | 1H NMR | 3 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| Quinoline | 13C NMR | 3 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| Imidazole | 1H NMR | 2 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| Imidazole | 13C NMR | 1 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| Pyrimidine | 1H NMR | 2 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| Pyrimidine | 13C NMR | 1 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| Purine | 1H NMR | 2 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| Purine | 13C NMR | 2 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| Benzoxazole | 1H NMR | 4 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| Benzoxazole | 13C NMR | 3 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| Quinoxaline | IR | 1 peak(s) unmatched | 1 extra predicted | - | ±50.0 |
| Quinoxaline | 1H NMR | 5 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| Quinoxaline | 13C NMR | 6 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| Diethyl ether | 1H NMR | 2 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| Diethyl ether | 13C NMR | 2 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| Methyl tert-butyl ether | 1H NMR | 3 peak(s) unmatched | 1 extra predicted | - | ±0.5 |
| Methyl tert-butyl ether | 13C NMR | 2 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| Aspirin | 1H NMR | 2 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| Aspirin | 13C NMR | 2 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| Benzyl acetate | 1H NMR | 4 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| Benzyl acetate | 13C NMR | 4 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| N-Methylacetamide | IR | 1 peak(s) unmatched | 1 extra predicted | - | ±50.0 |
| N-Methylacetamide | 13C NMR | 2 peak(s) unmatched | 2 extra predicted | - | ±5.0 |
| Nicotinamide | 1H NMR | 2 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| Nicotinamide | 13C NMR | 2 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| Phenol | 1H NMR | 4 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| Phenol | 13C NMR | 4 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| Aniline | 1H NMR | 4 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| Aniline | 13C NMR | 4 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| 2-Chloropyridine | 1H NMR | 1 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| 2-Chloropyridine | 13C NMR | 1 peak(s) unmatched | 1 extra predicted | - | ±5.0 |
| 4-Nitrophenol | 1H NMR | 3 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| 4-Nitrophenol | 13C NMR | 3 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| 2-Bromoethanol | IR | 1 peak(s) unmatched | 1 extra predicted | - | ±50.0 |
| 4-Chloroanisole | IR | 1 peak(s) unmatched | 1 extra predicted | - | ±50.0 |
| 4-Chloroanisole | 1H NMR | 3 peak(s) unmatched | 1 extra predicted | - | ±0.5 |
| 4-Chloroanisole | 13C NMR | 3 peak(s) unmatched | 1 extra predicted | - | ±5.0 |
| 1,4-Dioxane | 1H NMR | 3 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| 1,4-Dioxane | 13C NMR | 3 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| 1,3,5-Triazine | 1H NMR | 2 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| 1,3,5-Triazine | 13C NMR | 2 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| Benzimidazole | 1H NMR | 2 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| Benzimidazole | 13C NMR | 3 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| Coumarin | 1H NMR | 4 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| Coumarin | 13C NMR | 4 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| Naphthalene | 1H NMR | 7 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| Naphthalene | 13C NMR | 8 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| Phenanthrene | IR | 1 peak(s) unmatched | 1 extra predicted | - | ±50.0 |
| Phenanthrene | 1H NMR | 9 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| Phenanthrene | 13C NMR | 12 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| Indene | 1H NMR | 4 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| Indene | 13C NMR | 5 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| Quinazoline | 1H NMR | 4 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| Quinazoline | 13C NMR | 3 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| Isoquinoline | IR | 1 peak(s) unmatched | 1 extra predicted | - | ±50.0 |
| Isoquinoline | 1H NMR | 3 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| Isoquinoline | 13C NMR | 3 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| 1,4-Dimethoxybenzene | IR | 1 peak(s) unmatched | 1 extra predicted | - | ±50.0 |
| 1,4-Dimethoxybenzene | 1H NMR | 4 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| 1,4-Dimethoxybenzene | 13C NMR | 5 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| Cyclohexanone | 1H NMR | 3 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| Cyclohexanone | 13C NMR | 4 peak(s) unmatched | 1 extra predicted | - | ±5.0 |
| 2,4,6-Trinitrotoluene | IR | 1 peak(s) unmatched | 1 extra predicted | - | ±50.0 |
| 2,4,6-Trinitrotoluene | 1H NMR | 1 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| 2,4,6-Trinitrotoluene | 13C NMR | 3 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| 4-Vinylpyridine | 1H NMR | 3 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| 4-Vinylpyridine | 13C NMR | 3 peak(s) unmatched | 1 extra predicted | - | ±5.0 |
| 2-Methylfuran | 1H NMR | 2 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| 2-Methylfuran | 13C NMR | 1 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| 2-Bromopyridine | 1H NMR | 1 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| 2,6-Dichloropyridine | IR | 1 peak(s) unmatched | 1 extra predicted | - | ±50.0 |
| 2,6-Dichloropyridine | 1H NMR | 1 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| 2,6-Dichloropyridine | 13C NMR | 2 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| 4-Aminobenzoic acid | IR | 1 peak(s) unmatched | 1 extra predicted | - | ±50.0 |
| 4-Aminobenzoic acid | 1H NMR | 2 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| 4-Aminobenzoic acid | 13C NMR | 2 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| Ethyl 4-nitrobenzoate | 1H NMR | 2 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| Ethyl 4-nitrobenzoate | 13C NMR | 2 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| N,N-Dimethylacetamide | 1H NMR | 1 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| N,N-Dimethylacetamide | 13C NMR | 1 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| 4-Methoxybenzoic acid | IR | 2 peak(s) unmatched | 2 extra predicted | - | ±50.0 |
| 4-Methoxybenzoic acid | 1H NMR | 2 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| 4-Methoxybenzoic acid | 13C NMR | 4 peak(s) unmatched | 2 extra predicted | - | ±5.0 |
| 2-Methylpyridine | 1H NMR | 2 peak(s) unmatched | 1 extra predicted | - | ±0.5 |
| 2-Methylpyridine | 13C NMR | 1 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
| 3,4-Dimethoxybenzaldehyde | 1H NMR | 3 peak(s) unmatched | 0 extra predicted | - | ±0.5 |
| 3,4-Dimethoxybenzaldehyde | 13C NMR | 3 peak(s) unmatched | 0 extra predicted | - | ±5.0 |
## Sheet: Failures
| Molecule | Input SMILES | Canonical SMILES | Error |
| --- | --- | --- | --- |
| No failures. |  |  |  |