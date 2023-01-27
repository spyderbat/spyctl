import os
import shutil
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
TEST_CONTEXT2 = "__test_context2__"
CURR_PATH = Path.cwd()
WORKSPACE_DIR_NAME = "test_workspace__"
WORKSPACE_PATH = Path(f"./{WORKSPACE_DIR_NAME}")
WORKSPACE_CONFIG = Path(str(WORKSPACE_PATH.absolute()) + "/.spyctl/config")
CURRENT_CONTEXT = None


class SetupException(Exception):
    pass


def env_setup() -> bool:
    # Tests that the proper environment variables exist in pyproject.toml
    if not API_KEY or API_KEY == "__NONE__":
        print(
            "No api key provided. Edit the API_KEY environment variable in"
            " pyproject.toml"
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
            "No organization provided. Edit the ORG environment variable in"
            " pyproject.toml"
        )
        return False
    return True


def test_secrets():
    runner = CliRunner()
    test_key = "test_key"
    test_url = "https://test.url"
    # Test set a new secret
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
    assert f"Set new apisecret '{TEST_SECRET}' in" in result.output
    # Test getting all secrets
    result = runner.invoke(
        spyctl.main,
        [
            "config",
            "get-apisecrets",
        ],
    )
    assert TEST_SECRET in result.output
    # Test getting single secret
    result = runner.invoke(
        spyctl.main,
        [
            "config",
            "get-apisecrets",
            TEST_SECRET,
        ],
    )
    assert TEST_SECRET in result.output
    # Test getting single secret in yaml output
    result = runner.invoke(
        spyctl.main,
        [
            "config",
            "get-apisecrets",
            "-o",
            "yaml",
            TEST_SECRET,
        ],
    )
    assert TEST_SECRET in result.output
    assert API_KEY in result.output
    assert API_URL in result.output
    # Test updating a secret
    result = runner.invoke(
        spyctl.main,
        [
            "config",
            "set-apisecret",
            "-k",
            test_key,
            "-u",
            test_url,
            TEST_SECRET,
        ],
    )
    assert f"Updated apisecret '{TEST_SECRET}' in" in result.output
    result = runner.invoke(
        spyctl.main,
        [
            "config",
            "get-apisecrets",
            "-o",
            "yaml",
            TEST_SECRET,
        ],
    )
    assert TEST_SECRET in result.output
    assert test_key in result.output
    assert test_url in result.output
    # Test deleting a secret
    result = runner.invoke(
        spyctl.main,
        [
            "config",
            "delete-apisecret",
            "-y",
            TEST_SECRET,
        ],
    )
    assert f"Deleted secret '{TEST_SECRET}' from" in result.output
    result = runner.invoke(
        spyctl.main,
        [
            "config",
            "get-apisecrets",
        ],
    )
    assert TEST_SECRET not in result.output


def test_contexts():
    runner = CliRunner()
    create_secret()
    # Create a new context
    result = runner.invoke(
        spyctl.main,
        [
            "config",
            "set-context",
            "-s",
            TEST_SECRET,
            "-o",
            ORG,
            "-u",
            TEST_CONTEXT,
        ],
    )
    assert (
        f"Set new context '{TEST_CONTEXT}' in configuration file"
        in result.output
    )
    result = runner.invoke(
        spyctl.main,
        [
            "config",
            "set-context",
            "-s",
            TEST_SECRET,
            "-o",
            ORG,
            TEST_CONTEXT2,
        ],
    )
    # Test get all contexts
    test_str = f"*{TEST_CONTEXT}*{ORG}*0*"
    result = runner.invoke(
        spyctl.main,
        [
            "config",
            "get-contexts",
        ],
    )
    lines = result.output.splitlines()
    match = False
    for line in lines:
        if fnmatch(line, test_str):
            match = True
            assert "*" in line
            break
    assert match
    # Get specific contexts
    result = runner.invoke(
        spyctl.main,
        ["config", "get-contexts", TEST_CONTEXT],
    )
    assert fnmatch(result.output, test_str)
    # Display current context
    result = runner.invoke(
        spyctl.main,
        ["config", "current-context"],
    )
    assert result.output.strip("\n") == TEST_CONTEXT
    # Test use-context (switching contexts)
    result = runner.invoke(
        spyctl.main,
        ["config", "use-context", TEST_CONTEXT2],
    )
    assert f"Set current context to '{TEST_CONTEXT2}' in" in result.output
    result = runner.invoke(
        spyctl.main,
        ["config", "current-context"],
    )
    assert result.output.strip("\n") == TEST_CONTEXT2
    # Display config file
    result = runner.invoke(
        spyctl.main,
        ["config", "view"],
    )
    assert f"- name: {TEST_CONTEXT}" in result.output
    assert f"- name: {TEST_CONTEXT2}" in result.output
    # Delete contexts
    result = runner.invoke(
        spyctl.main,
        ["config", "delete-context", TEST_CONTEXT],
    )
    assert f"Deleted context '{TEST_CONTEXT}' in" in result.output
    result = runner.invoke(
        spyctl.main,
        ["config", "delete-context", TEST_CONTEXT2],
    )
    assert f"Deleted context '{TEST_CONTEXT2}' in" in result.output
    result = runner.invoke(
        spyctl.main,
        ["config", "get-contexts"],
    )
    assert TEST_CONTEXT not in result.output
    assert TEST_CONTEXT2 not in result.output


def test_workspace():
    create_secret()
    runner = CliRunner()
    # Test initialize a workspace
    result = runner.invoke(
        spyctl.main,
        [
            "config",
            "init-workspace",
        ],
    )
    test_str = (
        f"Created configuration file at */{WORKSPACE_DIR_NAME}/.spyctl/config*"
    )
    assert fnmatch(result.output, test_str)
    result = runner.invoke(
        spyctl.main,
        [
            "config",
            "set-context",
            "-s",
            TEST_SECRET,
            "-o",
            ORG,
            TEST_CONTEXT,
        ],
    )
    assert result.exit_code == 0
    result = runner.invoke(
        spyctl.main,
        [
            "config",
            "set-context",
            "-s",
            TEST_SECRET,
            "-o",
            ORG,
            TEST_CONTEXT2,
        ],
    )
    assert result.exit_code == 0
    # Create global contexts with the same name for testing purposes
    create_context(TEST_CONTEXT)
    create_context(TEST_CONTEXT2)
    # Get context from merged config
    result = runner.invoke(
        spyctl.main,
        [
            "config",
            "get-contexts",
            "-o",
            "wide",
            TEST_CONTEXT,
        ],
    )
    test_str = f"*/{WORKSPACE_DIR_NAME}/.spyctl/config*"
    assert TEST_CONTEXT in result.output
    assert fnmatch(result.output, test_str)
    # Delete global context by same name
    result = runner.invoke(
        spyctl.main,
        [
            "config",
            "delete-context",
            "-y",
            "-g",
            TEST_CONTEXT,
        ],
    )
    result = runner.invoke(
        spyctl.main,
        [
            "config",
            "get-contexts",
            "-g",
        ],
    )
    assert TEST_CONTEXT not in result.output
    result = runner.invoke(
        spyctl.main,
        [
            "config",
            "get-contexts",
        ],
    )
    assert TEST_CONTEXT in result.output
    # Delete workspace context
    result = runner.invoke(
        spyctl.main,
        [
            "config",
            "get-contexts",
            "-w",
        ],
    )
    assert TEST_CONTEXT2 in result.output
    result = runner.invoke(
        spyctl.main,
        [
            "config",
            "delete-context",
            "-y",
            TEST_CONTEXT2,
        ],
    )
    result = runner.invoke(
        spyctl.main,
        [
            "config",
            "get-contexts",
            "-w",
        ],
    )
    assert TEST_CONTEXT2 not in result.output
    # Set workspace current context to context within the global config
    result = runner.invoke(
        spyctl.main,
        [
            "config",
            "use-context",
            "-g",
            TEST_CONTEXT2,
        ],
    )
    test_str = (
        f"Set current context to '{TEST_CONTEXT2}' in configuration file"
    )
    assert test_str in result.output
    assert WORKSPACE_DIR_NAME not in result.output
    result = runner.invoke(
        spyctl.main,
        ["config", "current-context", "-g"],
    )
    assert TEST_CONTEXT2 == result.output.strip("\n")
    # Set workspace current context to context within the workspace config
    result = runner.invoke(
        spyctl.main,
        [
            "config",
            "use-context",
            TEST_CONTEXT,
        ],
    )
    test_str = f"Set current context to '{TEST_CONTEXT}' in configuration file"
    assert test_str in result.output
    assert WORKSPACE_DIR_NAME in result.output
    result = runner.invoke(
        spyctl.main,
        [
            "config",
            "current-context",
        ],
    )
    assert TEST_CONTEXT == result.output.strip("\n")
    # Test ensure unable to set global current context to context that
    # exists only in the local workspace config.
    result = runner.invoke(
        spyctl.main,
        [
            "config",
            "use-context",
            "-g",
            TEST_CONTEXT,
        ],
    )
    test_str = f"Unable to set current context '{TEST_CONTEXT}' for"
    assert test_str in result.output


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
    runner.invoke(
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
    runner.invoke(
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


def delete_context(name):
    runner = CliRunner()
    runner.invoke(
        spyctl.main,
        ["config", "delete-context", name],
    )


def current_context():
    runner = CliRunner()
    current_ctx = runner.invoke(
        spyctl.main,
        [
            "config",
            "current-context",
        ],
    ).output.strip("\n")
    return current_ctx


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
    # Set a global variable in configs.py to force reloading
    # the config file. Otherwise the global variable LOADED_CONFIG
    # remains set across invocations
    set_testing()


def teardown_module():
    delete_context(TEST_CONTEXT)
    delete_context(TEST_CONTEXT2)
    delete_secret()
    use_current_context()
    os.chdir(CURR_PATH)
    shutil.rmtree(WORKSPACE_PATH, ignore_errors=True)
