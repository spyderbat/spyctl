import os
import shutil
from fnmatch import fnmatch
from pathlib import Path
from itertools import groupby
import pytest
from pathlib import Path

from click.testing import CliRunner

from spyctl import spyctl
from spyctl.spyctl_lib import time_inp
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


def test_help():
    runner = CliRunner()
    response = runner.invoke(spyctl.main, ["-h"])
    assert response.exit_code == 0
    response = runner.invoke(spyctl.main, ["--help"])
    assert response.exit_code == 0
    response = runner.invoke(spyctl.main, ["get", "redflags", "--help"])
    assert response.exit_code == 0
    assert "Options for redflags:" in response.output
    response = runner.invoke(spyctl.main, ["config", "--help"])
    assert response.exit_code == 0


def test_get_namespaces():
    get_resource("namespaces", TWOHOURS)
    get_resource("namespaces", TWOHOURS + OUTYML)


TWOHOURS = ("-t", "2h")
OUTYML = ("-o", "yaml")


def remove_timestamps(str_list):
    rv = []
    for string in str_list:
        try:
            time_inp(string)
        except ValueError:
            rv.append(string)
    return rv


# asserts that the table has some population and returns
# name_or_id values that should give the first line again
def process_table_response(output: str):
    name_or_id_fields = (
        "NAME",
        "UID",
        "FLAG",
        "IMAGE",
    )
    lines = output.strip().splitlines()
    assert len(lines) > 1
    header_line, first_line = lines[:2]
    headers = []
    for non_empty_group, chars in groupby(
        enumerate(header_line), lambda x: not x[1].isspace()
    ):
        if non_empty_group:
            pos, header = next(chars)
            header += "".join(c for _, c in chars)
            headers.append((pos, header))
    rv = []
    for i, (pos, header) in enumerate(headers):
        if header in name_or_id_fields:
            next_pos = headers[i + 1][0] if i < len(headers) - 1 else None
            table_element = first_line[pos:next_pos].strip()
            rv.append(table_element)
    print(header_line)
    print(headers)
    assert len(rv) > 0
    comparison_line = remove_timestamps(first_line.split())
    return comparison_line, rv


resources = (
    "clusters",
    "machines",
    "policies",
    "pods",
    "nodes",
    "fingerprints",
    # "namespaces", # doesn't output a table
    "redflags",
    "opsflags",
)


@pytest.mark.parametrize("resource", resources)
def test_get_resources(resource):
    time_range = TWOHOURS
    output = OUTYML
    table = get_resource(resource, time_range)
    comparison_line, ids = process_table_response(table)
    for name_or_id in ids:
        single = get_resource(resource, time_range + (name_or_id,))
        first_output = remove_timestamps(single.splitlines()[1].split())
        assert first_output == comparison_line
    get_resource(resource, time_range + output)


def get_resource(resource, args=[], print_output=False):
    runner = CliRunner(mix_stderr=False)
    response = runner.invoke(spyctl.main, ["get", resource, *args])
    if print_output:
        print(response.output)
    assert response.exit_code == 0
    return response.stdout


resources_dir = Path(__file__).parent / "test_resources"


def test_create():
    runner = CliRunner()
    response = runner.invoke(
        spyctl.main,
        ["create", "policy", "-f", resources_dir / "test_baseline.yaml"],
    )
    assert response.exit_code == 0
    with open(resources_dir / "test_policy.yaml", "r") as f:
        assert response.output.strip("\n") == f.read().strip("\n")
    response = runner.invoke(
        spyctl.main,
        ["create", "baseline", "-f", resources_dir / "test_fprint_group.yaml"],
    )
    assert response.exit_code == 0
    with open(resources_dir / "test_baseline.yaml", "r") as f:
        assert response.output.strip("\n") == f.read().strip("\n")


def test_apply_delete():
    runner = CliRunner()
    response = runner.invoke(
        spyctl.main, ["apply", "-f", resources_dir / "test_policy.yaml"]
    )
    assert response.exit_code == 0
    assert response.output.startswith(
        "Successfully applied new policy with uid:"
    )
    response = runner.invoke(
        spyctl.main, ["get", "policies", "spyderbat-test"]
    )
    assert response.exit_code == 0
    assert "spyderbat-test" in response.output
    response = runner.invoke(
        spyctl.main, ["delete", "policy", "-y", "spyderbat-test"]
    )
    # assert response.exit_code == 0
    # assert response.output.startswith("Successfully deleted policy")


def test_diff():
    runner = CliRunner()
    response = runner.invoke(
        spyctl.main,
        [
            "diff",
            "-f",
            str(resources_dir) + "/test_baseline.yaml",
            "-w",
            str(resources_dir) + "/test_baseline_extra.yaml",
            "-y",
        ],
    )
    assert response.exit_code == 0
    assert "+     - name: python3.7" in response.output


def test_merge():
    runner = CliRunner()
    response = runner.invoke(
        spyctl.main,
        [
            "merge",
            "-f",
            str(resources_dir) + "/test_baseline.yaml",
            "-w",
            str(resources_dir) + "/test_baseline_extra.yaml",
            "-y",
        ],
    )
    assert response.exit_code == 0
    assert "\n    - name: python3.7" in response.output
    assert "\n    - name: sh" in response.output


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
    runner.invoke(
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
