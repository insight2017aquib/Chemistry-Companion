# NMR Serializer Forensics

## Target Function
serialize_analysis_result() in pi/serializers.py maps backend predictions to API payload via serialize_proton_nmr() and serialize_carbon_nmr().

## Proton NMR Payload
- **Before Serializer:** ProtonNMRPrediction(signals=[ProtonSignal(ppm_range=..., ppm_mid=...)], ...)
- **After Serializer (API Payload):**
`json
{
  "environments": [...],
  "signals": [
    {
      "label": "Aromatic CH",
      "ppm_range": [6.8, 7.6],
      "multiplicity": "m",
      "integration": 1,
      "ppm_mid": 7.2,
      "is_exchangeable": false
      // NO shift_ppm key exists
    }
  ],
  "disclaimer": "HEURISTIC ONLY ...",
  "summary_text": "..."
}
`
- **Field Name Check:** Nulls handled correctly. Nested structure preserved perfectly via .to_dict().
- **Mismatch Detected:** Backend does NOT output shift_ppm.

## Carbon NMR Payload
- **Before Serializer:** CarbonNMRPrediction(environments=[CarbonEnvironment(ppm_range=...)], ...)
- **After Serializer (API Payload):**
`json
{
  "environments": [
    {
      "label": "Ar CH carbon",
      "ppm_range": [122.0, 134.0],
      "carbon_count": 1
    }
  ],
  "disclaimer": "HEURISTIC ONLY ...",
  "summary_text": "..."
}
`
- **Field Name Check:** Keys match expectations exactly.
