from dataclasses import dataclass
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

@dataclass
class DockingPose:
    rank: int
    affinity_kcal: float
    rmsd_lb: float
    rmsd_ub: float
    pdbqt_block: str

def parse_vina_output(pdbqt_text: str) -> List[DockingPose]:
    """
    Splits multi-model PDBQT output from Vina into separate poses.
    Extracts VINA RESULT scores.
    """
    poses = []
    current_block: Optional[List[str]] = None
    
    # Defaults
    rank = 0
    affinity = 0.0
    rmsd_lb = 0.0
    rmsd_ub = 0.0

    if not pdbqt_text or not pdbqt_text.strip():
        return poses
    
    for line in pdbqt_text.splitlines():
        if line.startswith("MODEL"):
            current_block = [line]
            try:
                rank = int(line.split()[1])
            except (IndexError, ValueError):
                rank = len(poses) + 1
        elif line.startswith("REMARK VINA RESULT:"):
            # Format: REMARK VINA RESULT:    -7.1      0.000      0.000
            parts = line.split()[3:]
            if len(parts) >= 3:
                try:
                    affinity = float(parts[0])
                    rmsd_lb = float(parts[1])
                    rmsd_ub = float(parts[2])
                except ValueError:
                    logger.warning("Could not parse Vina score line: %s", line)
            if current_block is None:
                current_block = []
                rank = len(poses) + 1
            current_block.append(line)
        elif line.startswith("ENDMDL"):
            if current_block is not None:
                current_block.append(line)
                pose = DockingPose(
                    rank=rank or len(poses) + 1,
                    affinity_kcal=affinity,
                    rmsd_lb=rmsd_lb,
                    rmsd_ub=rmsd_ub,
                    pdbqt_block="\n".join(current_block) + "\n"
                )
                poses.append(pose)
            current_block = None
        else:
            if current_block is not None:
                current_block.append(line)
            elif line.startswith(("ATOM", "HETATM")):
                rank = len(poses) + 1
                current_block = [line]

    if current_block:
        pose = DockingPose(
            rank=rank or len(poses) + 1,
            affinity_kcal=affinity,
            rmsd_lb=rmsd_lb,
            rmsd_ub=rmsd_ub,
            pdbqt_block="\n".join(current_block) + "\n"
        )
        poses.append(pose)
                
    return poses
