import pytest

def test_seaborn_installed_for_benchmarks():
    """
    Ensure seaborn is installed to prevent the ModuleNotFoundError boundary cascade 
    in validation and benchmarks.
    """
    try:
        import seaborn as sns
    except ImportError:
        pytest.fail("Seaborn is not installed. Validation and Benchmarks will crash.")
        
def test_matplotlib_installed():
    """
    Ensure matplotlib is installed.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        pytest.fail("Matplotlib is not installed.")
