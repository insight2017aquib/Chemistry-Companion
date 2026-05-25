from pydantic import BaseModel
from typing import List, Dict, Any

class DockingExplanationRequest(BaseModel):
    smiles: str
    poses: List[Dict[str, Any]]
    interactions: List[Dict[str, Any]]
    
class PoseExplanationRequest(BaseModel):
    smiles: str
    pose: Dict[str, Any]
    interactions: List[Dict[str, Any]]

class DockingExplanationResponse(BaseModel):
    explanation: str
