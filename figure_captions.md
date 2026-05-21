# Publication Figure Captions

The following captions correspond to the generated SVG figures located in `outputs/spectra/publication_plots/` and `outputs/comparison/publication_plots/`.

## Spectra Validation Workflow
**Figure 1: Mean Error Magnitude Overview (`01_mae_rmse_overview.svg`)**
Bar chart depicting the Mean Absolute Error (MAE, solid bars) and Root Mean Square Error (RMSE, hatched bars) for heuristic predictions across the Infrared (IR), ¹H NMR, and ¹³C NMR domains.

**Figure 2: Experimental Coverage Heatmap (`02_coverage_heatmap.svg`)**
Heatmap displaying the fraction of experimental reference peaks successfully matched by the heuristic predictions for each molecule across the three spectral domains. 

**Figure 3: IR Peak Scatter Correlation (`03_ir_scatter.svg`)**
Scatter plot comparing heuristically predicted IR wavenumbers against experimental reference values. The identity line (dashed gold) indicates perfect correlation.

**Figure 4: ¹H NMR Shift Scatter Correlation (`04_1h_scatter.svg`)**
Scatter plot of predicted versus experimental ¹H NMR chemical shifts (ppm).

**Figure 5: ¹³C NMR Shift Scatter Correlation (`05_13c_scatter.svg`)**
Scatter plot of predicted versus experimental ¹³C NMR chemical shifts (ppm).

**Figure 6: Error Distribution KDE (`06_error_distributions.svg`)**
Histograms and Kernel Density Estimates (KDE) representing the distribution of absolute errors across the three spectral domains. The dashed gold line indicates the mean absolute error.

**Figure 7: False Negative Bar Chart (`07_missing_predictions.svg`)**
Stacked bar chart illustrating the count of experimental peaks (False Negatives) that failed to be matched by the heuristic predictor within the defined tolerance limits for each molecule.

**Figure 8: Domain Coverage Radar (`08_coverage_radar.svg`)**
Radar plot comparing the overall predicted coverage (fraction of predicted peaks matched) against experimental coverage (fraction of experimental peaks matched) across the IR, ¹H NMR, and ¹³C NMR domains.

## Tool Comparison Benchmark
**Figure 9: Processing Speed Comparison (`01_speed_comparison.svg`)**
Bar chart comparing the batch processing throughput (molecules per second) of Chemistry Companion against native RDKit and Open Babel implementations, encompassing SMILES parsing, 2D descriptor generation, and functional group categorization.

**Figure 10: Qualitative Feature Radar (`02_feature_radar.svg`)**
Radar plot evaluating the maturity of qualitative features (Batch Workflow, Exports & Reports, Docking Preparation, GUI Integration) across the three tools on a normalized 0–3 scale.

**Figure 11: Native Descriptive Features (`03_descriptor_fg_counts.svg`)**
Clustered bar chart detailing the count of natively calculated chemical descriptors and distinctly categorized functional groups provided out-of-the-box by each cheminformatics tool.
