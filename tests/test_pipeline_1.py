# test_pipeline_1.py

from core.pipeline import ChemistryPipeline
from core.config import get_settings

def main():
    # Load settings
    settings = get_settings()

    # Initialize pipeline correctly
    # If ChemistryPipeline expects a config object, pass it positionally
    pipeline = ChemistryPipeline(settings)

    # Process a simple SMILES (benzene)
    result = pipeline.process_smiles("c1ccccc1")

    # Print outputs
    print("Pipeline result descriptors:", result.descriptors.to_dict())
    print("IR prediction summary:", result.ir_prediction.summary_text)
    print("¹H NMR prediction summary:", result.proton_nmr_prediction.summary_text)
    print("¹³C NMR prediction summary:", result.carbon_nmr_prediction.summary_text)

if __name__ == "__main__":
    main()
