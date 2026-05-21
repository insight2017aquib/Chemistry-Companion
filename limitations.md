# Limitations and Caveats

While Chemistry Companion provides a rapid, integrated pipeline for structural analysis and spectral prediction, it relies on heuristic and empirical approaches that introduce specific scientific and technical limitations. Users must be aware of these constraints to avoid overinterpreting the generated results.

## 1. Spectral Prediction Limitations
- **Heuristic, Not Quantum Mechanical**: The IR and NMR spectral predictions are derived from empirically curated rule sets (substructure/SMARTS matching) rather than *ab initio* quantum mechanical calculations (e.g., Density Functional Theory). 
- **Conformational Independence**: Predictions are generated purely from 2D topological connectivity. They do not account for 3D conformational ensembles, intramolecular hydrogen bonding, steric crowding, or solvent effects, all of which significantly perturb experimental chemical shifts and vibrational frequencies.
- **Novel Chemical Spaces**: The accuracy of the predictor drops for highly exotic, strained, or uniquely conjugated systems that fall outside standard heuristic training sets.

## 2. Functional Group Detection
- **Stereochemical Agnosticism**: The current functional group detector and descriptor generator do not differentiate between stereoisomers (enantiomers, diastereomers) or geometric isomers ($E$/$Z$).
- **Tautomerization**: The pipeline evaluates the explicit tautomer provided in the input SMILES. It does not natively explore tautomeric equilibria, which may result in missing functional groups that are present in solution.

## 3. Descriptor Calculation
- **2D Topological Focus**: The calculated descriptors (e.g., LogP, TPSA, exact mass) rely on the RDKit 2D descriptor engine. They are robust for standard Lipinski profiling but lack 3D structural descriptors (e.g., solvent-accessible surface area, principal moments of inertia) unless external 3D conformer generation is explicitly invoked.

## 4. Docking Preparation and Charge Assignment
- **Charge Model Constraints**: The automated docking preparation pipeline utilizes Open Babel to assign Gasteiger (empirical partial equalization of orbital electronegativities) charges. While sufficient for rigid-receptor docking protocols like AutoDock Vina, these charges are not derived from high-level electrostatic potential (ESP) mapping and may be inadequate for highly polarized or charged transition states.
- **Protonation States**: Protonation is applied heuristically at a physiological pH (7.4) using Open Babel's internal rules. For proteins or complex polyprotic small molecules, explicit `pKa` calculations using dedicated tools (e.g., Epik, PropKa) are recommended prior to docking.

## 5. Performance and Scaling
- **Throughput Profiling**: Chemistry Companion is heavily optimized for batch processing of small-to-medium libraries (10² to 10⁴ compounds). While its native batching reduces boilerplate code, it scales linearly with CPU cores and is not currently architected for distributed cluster computing (e.g., MPI or GPU-accelerated molecular dynamics).

## Conclusion
Chemistry Companion is designed to serve as a rapid, first-pass analytical tool and educational framework. It successfully bridges the gap between raw cheminformatics libraries and end-user workflows. However, for publication-grade validation of novel compounds, its heuristic outputs must be corroborated with rigorous experimental data (e.g., acquired NMR, IR) or high-level computational methods (e.g., DFT).
