#! /home/brhaub/spyctl_demo/bin/python3

import os
import shutil
import sys
from fnmatch import fnmatch
from pathlib import Path

from click.testing import CliRunner

from spyctl import spyctl
from spyctl.config.configs import CURR_CONTEXT_NONE, set_testing


API_KEY = os.environ.get("API_KEY")
API_URL = os.environ.get("API_URL")
ORG = os.environ.get("ORG")
TEST_SECRET = "__test_secret__"
TEST_CONTEXT = "__test_context__"
CURR_PATH = Path.cwd()
WORKSPACE_DIR_NAME = "test_workspace__"
WORKSPACE_PATH = Path(f"./{WORKSPACE_DIR_NAME}")
WORKSPACE_CONFIG = Path(str(WORKSPACE_PATH.absolute()) + "/.spyctl/config")
CURRENT_CONTEXT = None


class SetupException(Exception):
    pass


def test_version():
    runner = CliRunner()
    response = runner.invoke(spyctl.main, ["-v"])
    test_pat = "Spyctl, version *.*.*"
    assert response.exit_code == 0
    assert fnmatch(response.output, test_pat)
    response = runner.invoke(spyctl.main, ["--version"])
    test_pat = "Spyctl, version *.*.*"
    assert response.exit_code == 0
    assert fnmatch(response.output, test_pat)


def test_get_clusters():
    runner = CliRunner()
    response = runner.invoke(spyctl.main, ["get", "clusters"])
    assert response.exit_code == 0


def test_get_machines():
    runner = CliRunner()
    response = runner.invoke(spyctl.main, ["get", "machines"])
    assert response.exit_code == 0


def test_get_policies():
    runner = CliRunner()
    response = runner.invoke(spyctl.main, ["get", "policies"])
    assert response.exit_code == 0


def test_get_pods():
    runner = CliRunner()
    response = runner.invoke(spyctl.main, ["get", "pods"])
    assert response.exit_code == 0


def test_get_pods_2hrs():
    runner = CliRunner()
    response = runner.invoke(spyctl.main, ["get", "pods", "-t", "2h"])
    assert response.exit_code == 0


def test_get_pods_25hrs():
    runner = CliRunner()
    response = runner.invoke(spyctl.main, ["get", "pods", "-t", "25h"])
    print(response.output)
    assert response.exit_code == 0


def test_get_pods_2weeks():
    runner = CliRunner()
    response = runner.invoke(spyctl.main, ["get", "pods", "-t", "2w"])
    print(response.output)
    assert response.exit_code == 0


def test_get_fingerprints():
    runner = CliRunner()
    response = runner.invoke(spyctl.main, ["get", "fingerprints"])
    print(response.output)
    assert response.exit_code == 0


def test_get_fingerprints_2hrs():
    runner = CliRunner()
    response = runner.invoke(spyctl.main, ["get", "fingerprints", "-t", "2h"])
    print(response.output)
    assert response.exit_code == 0


def test_get_fingerprints_25hrs():
    runner = CliRunner()
    response = runner.invoke(spyctl.main, ["get", "fingerprints", "-t", "25h"])
    print(response.output)
    assert response.exit_code == 0


def test_get_fingerprints_2weeks():
    runner = CliRunner()
    response = runner.invoke(spyctl.main, ["get", "fingerprints", "-t", "2w"])
    print(response.output)
    assert response.exit_code == 0


def test_get_namespaces():
    runner = CliRunner()
    response = runner.invoke(spyctl.main, ["get", "namespaces"])
    print(response.output)
    assert response.exit_code == 0


def test_get_namespaces_2hrs():
    runner = CliRunner()
    response = runner.invoke(spyctl.main, ["get", "namespaces", "-t", "2h"])
    print(response.output)
    assert response.exit_code == 0


def test_get_namespaces_25hrs():
    runner = CliRunner()
    response = runner.invoke(spyctl.main, ["get", "namespaces", "-t", "25h"])
    print(response.output)
    assert response.exit_code == 0


def test_get_namespaces_2weeks():
    runner = CliRunner()
    response = runner.invoke(spyctl.main, ["get", "namespaces", "-t", "2w"])
    print(response.output)
    assert response.exit_code == 0


def env_setup() -> bool:
    # Tests that the proper environment variables exist in pyproject.toml
    if not API_KEY or API_KEY == "__NONE__":
        print(
            "No api key provided. Edit the API_KEY environment variable in pyproject.toml"
        )
        return False
    if not API_URL or API_URL == "__NONE__":
        print(
            "No api url provided. Edit the API_URL environment variable in"
            ' pyproject.toml to "API_URL=https://api.spyderbat.com"'
        )
        return False
    if not ORG or ORG == "__NONE__":
        print(
            "No organization provided. Edit the ORG environment variable in pyproject.toml"
        )
        return False
    return True


def create_secret():
    runner = CliRunner()
    result = runner.invoke(
        spyctl.main,
        [
            "config",
            "set-apisecret",
            "-k",
            API_KEY,
            "-u",
            API_URL,
            TEST_SECRET,
        ],
    )
    if result.exit_code != 0:
        raise SetupException("Unable to create test secret")


def delete_secret():
    runner = CliRunner()
    result = runner.invoke(
        spyctl.main,
        [
            "config",
            "delete-apisecret",
            "-y",
            TEST_SECRET,
        ],
    )


def create_context(name):
    runner = CliRunner()
    result = runner.invoke(
        spyctl.main,
        [
            "config",
            "set-context",
            "-s",
            TEST_SECRET,
            "-o",
            ORG,
            "-g",
            name,
        ],
    )
    if result.exit_code != 0:
        raise SetupException("Unable to create test context")


def delete_context(name):
    runner = CliRunner()
    result = runner.invoke(
        spyctl.main,
        ["config", "delete-context", name],
    )


def current_context():
    runner = CliRunner()
    result = runner.invoke(
        spyctl.main,
        [
            "config",
            "current-context",
        ],
    )
    if result.exit_code != 0:
        raise SetupException("Unable get current context")
    current_ctx = result.output.strip("\n")
    return current_ctx


def use_test_context(name):
    runner = CliRunner()
    runner.invoke(spyctl.main, ["config", "use-context", name])


def use_current_context():
    if CURRENT_CONTEXT:
        runner = CliRunner()
        runner.invoke(spyctl.main, ["config", "use-context", CURRENT_CONTEXT])


def setup_module():
    if not env_setup():
        raise SetupException("Check environment variables in pyproject.toml")
    global CURRENT_CONTEXT
    current_ctx = current_context()
    if current_ctx and current_ctx != CURR_CONTEXT_NONE:
        CURRENT_CONTEXT = current_ctx
    if WORKSPACE_PATH.exists():
        teardown_module()
        raise SetupException("Workspace path already exists")
    WORKSPACE_PATH.mkdir(exist_ok=False)
    os.chdir(WORKSPACE_PATH)
    create_secret()
    create_context(TEST_CONTEXT)
    use_test_context(TEST_CONTEXT)
    # Set a global variable in configs.py to force reloading
    # the config file. Otherwise the global variable LOADED_CONFIG
    # remains set across invocations
    set_testing()


def teardown_module():
    delete_context(TEST_CONTEXT)
    delete_secret()
    use_current_context()
    os.chdir(CURR_PATH)
    shutil.rmtree(WORKSPACE_PATH, ignore_errors=True)
