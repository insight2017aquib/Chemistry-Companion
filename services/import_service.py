"""
services/import_service.py
==========================
Handles importing MedChem datasets from CSV/Excel files into a ChemicalSeries.
Includes smart column mapping and biological activity normalization.
"""

import io
import math
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from database.models import SeriesCompound

logger = logging.getLogger(__name__)

class ImportService:
    def __init__(self, db: Session, medchem_service):
        self.db = db
        self.medchem = medchem_service

    def normalize_activity(self, activity_type: str, value: float, unit: str) -> Optional[float]:
        """
        Normalizes generic biological data into a standardized -log10 scale (pIC50/pKi).
        """
        if not value or value <= 0:
            return None
            
        activity_type = activity_type.upper()
        unit = unit.lower()
        
        # Convert everything to Molar first if it's IC50/Ki/MIC
        if activity_type in ["IC50", "KI", "MIC", "EC50", "CC50", "MBC"]:
            molar_value = value
            if unit in ["nm", "nmol/l"]:
                molar_value = value * 1e-9
            elif unit in ["um", "umol/l", "µm"]:
                molar_value = value * 1e-6
            elif unit in ["mm", "mmol/l"]:
                molar_value = value * 1e-3
                
            try:
                return -math.log10(molar_value)
            except ValueError:
                return None
        
        # If it's already a p-value (pIC50, pKi), just return the value
        if activity_type in ["PIC50", "PKI"]:
            return value
            
        # For % inhibition or docking scores, we don't normalize to a p-value in the same way,
        # but we can return it as-is for the normalized field to allow sorting.
        return value

    def parse_file(self, file_bytes: bytes, filename: str) -> List[Dict[str, Any]]:
        """Parses CSV or Excel into a list of dictionaries."""
        try:
            import pandas as pd
        except ImportError:
            logger.error("Pandas is not installed. Data import requires pandas.")
            raise RuntimeError("Pandas is not installed. Please run `pip install pandas openpyxl`.")
            
        try:
            if filename.endswith(".csv"):
                df = pd.read_csv(io.BytesIO(file_bytes))
            elif filename.endswith(".xlsx"):
                df = pd.read_excel(io.BytesIO(file_bytes))
            else:
                raise ValueError("Unsupported file format. Please upload .csv or .xlsx")
                
            # Clean dataframe: replace NaNs with None
            df = df.where(pd.notnull(df), None)
            return df.to_dict('records')
        except Exception as e:
            logger.error(f"Failed to parse file: {e}")
            raise

    def import_dataset(self, series_id: str, file_bytes: bytes, filename: str, column_map: Dict[str, str]) -> Dict[str, Any]:
        """
        Imports the dataset into the database using the provided column mapping.
        column_map example:
        {
            "smiles_col": "Structure",
            "name_col": "Compound ID",
            "activity_val_col": "IC50",
            "activity_unit": "nM",
            "activity_type": "IC50",
            "docking_col": "Vina Score",
            "notes_col": "Observations"
        }
        """
        records = self.parse_file(file_bytes, filename)
        
        smiles_col = column_map.get("smiles_col")
        name_col = column_map.get("name_col")
        val_col = column_map.get("activity_val_col")
        dock_col = column_map.get("docking_col")
        notes_col = column_map.get("notes_col")
        
        act_type = column_map.get("activity_type", "IC50")
        act_unit = column_map.get("activity_unit", "nM")
        
        imported_count = 0
        skipped_count = 0
        
        for row in records:
            smiles = str(row.get(smiles_col, "")) if smiles_col in row and row[smiles_col] else None
            
            if not smiles:
                skipped_count += 1
                continue
                
            name = str(row.get(name_col, f"Compound_{imported_count+1}")) if name_col in row and row[name_col] else f"Compound_{imported_count+1}"
            
            act_val = None
            if val_col in row and row[val_col] is not None:
                try:
                    act_val = float(row[val_col])
                except (ValueError, TypeError):
                    pass
                    
            dock_val = str(row.get(dock_col, "")) if dock_col in row and row[dock_col] else None
            notes = str(row.get(notes_col, "")) if notes_col in row and row[notes_col] else None
            
            normalized_val = self.normalize_activity(act_type, act_val, act_unit) if act_val is not None else None
            
            # Use MedchemService to add the compound so it calculates properties
            # Note: We modified medchem_service.add_compound signature in the previous step,
            # so we need to ensure medchem_service.py is updated to accept the new arguments.
            self.medchem.add_compound_advanced(
                series_id=series_id,
                smiles=smiles,
                name=name,
                activity_type=act_type if act_val is not None else None,
                activity_value=act_val,
                activity_unit=act_unit if act_val is not None else None,
                normalized_value=normalized_val,
                docking_affinity=dock_val,
                notes=notes,
                tags=["Imported"]
            )
            imported_count += 1
            
        return {
            "status": "success",
            "imported_count": imported_count,
            "skipped_count": skipped_count
        }
