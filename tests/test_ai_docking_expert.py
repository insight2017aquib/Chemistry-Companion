import pytest
from unittest.mock import MagicMock, patch

from services.ai.docking_expert import DockingExpertService
from services.ai.models import AIResponse

@pytest.fixture
def expert_service():
    # Mock the AI provider manager so we don't make real API calls during tests
    mock_provider = MagicMock()
    mock_provider.query.return_value = AIResponse(
        text="Mocked expert response.",
        provider_used="mock",
    )
    return DockingExpertService(provider_manager=mock_provider)

def test_explain_pose(expert_service):
    interactions = [
        {"type": "Hydrogen Bond", "protein_residue": "TYR 101", "distance": 2.5}
    ]
    pose = {"rank": 1, "affinity": -9.5}
    
    response = expert_service.explain_pose("CCO", pose, interactions)
    
    assert response.text == "Mocked expert response."
    expert_service.ai.query.assert_called_once()
    
    # Verify strict prompt rules are included
    prompt_used = expert_service.ai.query.call_args[0][0]
    assert "absolute truth derived from rigid physical physics engines" in prompt_used
    assert "-9.5" in prompt_used
    assert "TYR 101" in prompt_used

def test_compare_poses(expert_service):
    poses = [
        {"rank": 1, "affinity": -9.5},
        {"rank": 2, "affinity": -8.0}
    ]
    interactions_dict = {
        1: [{"type": "Hydrogen Bond", "protein_residue": "TYR 101"}],
        2: [{"type": "Hydrophobic", "protein_residue": "LEU 50"}]
    }
    
    response = expert_service.compare_poses("CCO", poses, interactions_dict)
    
    assert response.text == "Mocked expert response."
    prompt_used = expert_service.ai.query.call_args[0][0]
    assert "Compare the following 2 docking poses" in prompt_used

def test_suggest_improvements(expert_service):
    interactions = [{"type": "Hydrogen Bond", "protein_residue": "TYR 101"}]
    pose = {"rank": 1, "affinity": -9.5}
    
    response = expert_service.suggest_improvements("CCO", pose, interactions)
    
    assert response.text == "Mocked expert response."
    prompt_used = expert_service.ai.query.call_args[0][0]
    assert "Do NOT generate modified SMILES strings" in prompt_used

def test_generate_report(expert_service):
    job_metadata = {"receptor_name": "target_protein", "ligand_name": "drug_candidate"}
    poses = [{"rank": 1, "affinity": -9.5}]
    interactions_dict = {1: [{"type": "Hydrogen Bond", "protein_residue": "TYR 101"}]}
    
    response = expert_service.generate_report(job_metadata, poses, interactions_dict)
    
    assert response.text == "Mocked expert response."
    prompt_used = expert_service.ai.query.call_args[0][0]
    assert "Executive Summary report" in prompt_used
    assert "target_protein" in prompt_used
