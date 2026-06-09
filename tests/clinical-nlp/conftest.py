import pytest
from src.agents import ClinicalWorkflow

@pytest.fixture(scope="session")
def workflow():
    wf = ClinicalWorkflow()
    return wf
