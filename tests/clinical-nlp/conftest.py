import pytest
import os
from src.agents import ClinicalWorkflow

@pytest.fixture(scope="session")
def workflow():
    os.environ["SARVAM_API_KEY"] = "ci-test-key"
    wf = ClinicalWorkflow()
    return wf
