from apeye.api import ApeyeApi, ApeyeApiMethod
import json
import pytest

# Expected tree() output.  If the test config is changed, this will change.
# {
#     "classes": {
#         "hasmethods": {
#             "methods": [
#                 test.hasmethods.list,
#                 test.hasmethods.get,
#                 test.hasmethods.create,
#                 test.hasmethods.update,
#                 test.hasmethods.delete,
#             ]
#         },
#         "container": {
#             "classes": {
#                 "subcontainer": {
#                     "methods": [
#                         test.subcontainer.list,
#                         test.subcontainer.get,
#                         test.subcontainer.create,
#                         test.subcontainer.update,
#                         test.subcontainer.delete,
#                     ]
#                 },
#                 "subcontainer2": {
#                     "methods": [
#                         test.subcontainer2.list,
#                         test.subcontainer2.get,
#                         test.subcontainer2.create,
#                         test.subcontainer2.update,
#                         test.subcontainer2.delete,
#                     ]
#                 },
#                 "nomodel": {"methods": [test.nomodel.list]},
#             }
#         },
#     }
# }


@pytest.mark.parametrize(
    "env",
    ["basic", "param", "header", "no_auth", "no_models", "use_session", "no_headers"],
)
def test_available_environments(env):
    testservice = ApeyeApi(config_file="test/data/api/testservice.yml", environment=env)

    # Objects in the tree are generated so we can't test the specific instances but
    # we know how many there should be, and their type
    mytree = testservice.tree()
    assert len(mytree) == 1
    assert len(mytree["classes"]["hasmethods"]["methods"]) == 5
    assert len(mytree["classes"]["container"]["classes"]) == 3
    assert (
        len(mytree["classes"]["container"]["classes"]["subcontainer"]["methods"]) == 5
    )
    assert (
        len(mytree["classes"]["container"]["classes"]["subcontainer2"]["methods"]) == 5
    )

    allmethods = (
        mytree["classes"]["hasmethods"]["methods"]
        + mytree["classes"]["container"]["classes"]["subcontainer"]["methods"]
        + mytree["classes"]["container"]["classes"]["subcontainer2"]["methods"]
    )

    for mth in allmethods:
        assert type(mth) is ApeyeApiMethod


@pytest.mark.parametrize(
    "env",
    ["basic", "param", "header", "no_auth", "no_models", "use_session", "no_headers"],
)
def test_named_methods(env):
    testservice = ApeyeApi(config_file="test/data/api/testservice.yml", environment=env)

    assert type(testservice.hasmethods.update) is ApeyeApiMethod


def test_to_json():
    testservice = ApeyeApi(
        config_file="test/data/api/testservice.yml", environment="basic"
    )

    # Arbtrarily chosen method, just to test json output
    assert json.loads(testservice.hasmethods.update.to_json()) == {
        'scheme': 'https',
        'host': 'api.example.com',
        'port': 443,
        'credentials': {'username': 'fakeuser', 'password': 'fakepassword'},
        'url': 'https://api.example.com:443/api/things/:id',
        'method_data': {
            'default_tokens': {'otherthing': 'changedstuff'},
            'method': 'PUT',
            'path': '/things/:id',
            'return': 200
        },
    }

def test_path_tokens():
    testservice = ApeyeApi(
        config_file="test/data/api/testservice.yml", environment="basic"
    )

    assert testservice.hasmethods.update.path_tokens() == ['lots', 'of', 'tokens']