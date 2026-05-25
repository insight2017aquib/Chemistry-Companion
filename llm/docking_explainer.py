from typing import List, Dict, Any
import json
from services.llm_service import get_llm_client

def explain_docking_result(poses: List[Dict[str, Any]], interactions: List[Dict[str, Any]], smiles: str) -> str:
    """
    Builds a structured prompt from full docking data and calls the configured LLM provider.
    """
    client = get_llm_client()
    
    prompt = f"""
    You are an expert medicinal chemist. Analyze the following molecular docking results.
    
    Ligand SMILES: {smiles}
    
    Top Poses:
    {json.dumps(poses[:5], indent=2)}
    
    Key Interactions (Mocked):
    {json.dumps(interactions, indent=2)}
    
    Please provide a concise but professional summary of the binding affinity, 
    the significance of the interactions, and the overall viability of this ligand.
    """
    
    return client.explain(prompt)

def explain_single_pose(pose: Dict[str, Any], interactions: List[Dict[str, Any]], smiles: str) -> str:
    """
    Builds a structured prompt for a single pose and calls the configured LLM provider.
    """
    client = get_llm_client()
    
    prompt = f"""
    You are an expert medicinal chemist. Analyze this specific docking pose.
    
    Ligand SMILES: {smiles}
    
    Pose Details:
    Rank: {pose.get('rank')}
    Affinity: {pose.get('affinity')} kcal/mol
    
    Key Interactions (Mocked):
    {json.dumps(interactions, indent=2)}
    
    Explain why this specific pose might be favorable or unfavorable.
    """
    
    return client.explain(prompt)
