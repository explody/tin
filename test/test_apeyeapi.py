from apeye.api import ApeyeApi
import pytest


@pytest.mark.parametrize("env", ['basic', 'param', 'header', 'no_models'])
def test_available_environments(env):
    myapi = ApeyeApi(config_file='test/data/api/test.yml', environment=env)
    assert type(myapi) is ApeyeApi
