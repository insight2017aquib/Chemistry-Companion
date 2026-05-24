# NMR Contract Trace

## Proton (1H) NMR Path
- **Backend Field:** ProtonNMRPrediction.signals (list of ProtonSignal)
- **ProtonSignal Fields:** label, ppm_range, multiplicity, integration, description, ationale, ppm_mid, nnotation, environment_class, confidence, is_exchangeable, is_approximate, disclaimer
- **Serializer Field:** Passes fields directly via .to_dict()
- **API Field:** Passes fields directly to payload under proton_nmr_prediction.signals
- **Template Field:** spectrum_accordion.html expects sig.get('shift_ppm')
- **DOM Render Result:** Field drift! The template asks for shift_ppm instead of ppm_range or ppm_mid, causing the template to fall back to —.

## Carbon (13C) NMR Path
- **Backend Field:** CarbonNMRPrediction.environments (list of CarbonEnvironment)
- **CarbonEnvironment Fields:** label, ppm_range, description, ationale, tom_indices, carbon_count, ppm_mid, nnotation, environment_class, confidence, hybridization, is_aromatic, is_heteroaromatic, heterocycle_family, hetero_position, ing_size, ttached_elements, 
_attached_h, is_quaternary, carbonyl_type, is_approximate, disclaimer
- **Serializer Field:** Passes fields directly via .to_dict()
- **API Field:** Passes fields directly to payload under carbon_nmr_prediction.environments
- **Template Field:** spectrum_accordion.html correctly calls env.get('ppm_range') and env.get('carbon_count')
- **DOM Render Result:** Matches exactly. BUT nalysis_results.html routes to spectrum_accordion.html which completely omits rendering the disclaimer and summary text for both NMR spectrums, leading to an incomplete frontend display.
