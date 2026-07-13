"""
services/figure_service.py
==========================
Generates PNG/SVG figures for Publications using matplotlib.
"""

import os
import uuid
from typing import List
from sqlalchemy.orm import Session
from database.models import FigureAsset, SeriesCompound

try:
    import matplotlib
    matplotlib.use('Agg') # Headless
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class FigureService:
    def __init__(self, db: Session):
        self.db = db
        # Ensure a directory exists for outputting images
        self.output_dir = "static/figures"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)

    def generate_property_correlation(self, workspace_id: str, compounds: List[SeriesCompound], x_prop: str = "logp", y_prop: str = "mw", format_ext: str = "png") -> FigureAsset:
        """
        Generates a scatter plot correlating two physical properties (or pIC50).
        """
        if not MATPLOTLIB_AVAILABLE:
            raise ImportError("matplotlib is not installed.")

        x_vals = []
        y_vals = []
        
        for c in compounds:
            props = c.properties or {}
            
            # Extract X
            if x_prop == "pic50":
                x = c.normalized_value or 0
            else:
                x = props.get(x_prop, 0)
                
            # Extract Y
            if y_prop == "pic50":
                y = c.normalized_value or 0
            else:
                y = props.get(y_prop, 0)
                
            x_vals.append(x)
            y_vals.append(y)

        plt.figure(figsize=(6, 4))
        plt.scatter(x_vals, y_vals, c='indigo', alpha=0.6, edgecolors='w')
        plt.xlabel(x_prop.upper())
        plt.ylabel(y_prop.upper())
        plt.title(f"Property Correlation: {y_prop.upper()} vs {x_prop.upper()}")
        plt.grid(True, linestyle='--', alpha=0.5)
        plt.tight_layout()

        filename = f"fig_{uuid.uuid4().hex[:10]}.{format_ext}"
        filepath = os.path.join(self.output_dir, filename)
        
        plt.savefig(filepath, format=format_ext, dpi=300)
        plt.close()

        # Save Asset
        fig = FigureAsset(
            id=f"figas_{uuid.uuid4().hex[:10]}",
            workspace_id=workspace_id,
            title=f"Correlation {y_prop.upper()} vs {x_prop.upper()}",
            figure_type="Scatter Plot",
            file_path=filepath
        )
        self.db.add(fig)
        self.db.commit()
        
        return fig
