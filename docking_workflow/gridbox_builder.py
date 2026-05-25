from dataclasses import dataclass

@dataclass
class GridBoxConfig:
    center_x: float
    center_y: float
    center_z: float
    size_x: float
    size_y: float
    size_z: float
    spacing: float = 0.375


def _parse_pdbqt_coordinates(line: str):
    try:
        return float(line[30:38]), float(line[38:46]), float(line[46:54])
    except ValueError:
        parts = line.split()
        coords = []
        for token in parts[4:]:
            if "." not in token:
                continue
            coords.append(float(token))
            if len(coords) == 3:
                return coords[0], coords[1], coords[2]
        raise

def auto_gridbox(pdbqt_text: str, margin: float = 5.0) -> GridBoxConfig:
    """
    Auto-detects gridbox bounding box from coordinates in PDBQT.
    Useful for blind docking or if ligand is extracted.
    """
    xs, ys, zs = [], [], []
    
    for line in pdbqt_text.splitlines():
        if line.startswith("ATOM") or line.startswith("HETATM"):
            try:
                x, y, z = _parse_pdbqt_coordinates(line)
                xs.append(x)
                ys.append(y)
                zs.append(z)
            except (IndexError, ValueError):
                continue
                
    if not xs:
        raise ValueError("No coordinates found in PDBQT to generate gridbox")
        
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    min_z, max_z = min(zs), max(zs)
    
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2
    center_z = (min_z + max_z) / 2
    
    size_x = (max_x - min_x) + margin * 2
    size_y = (max_y - min_y) + margin * 2
    size_z = (max_z - min_z) + margin * 2
    
    return GridBoxConfig(center_x, center_y, center_z, size_x, size_y, size_z)
