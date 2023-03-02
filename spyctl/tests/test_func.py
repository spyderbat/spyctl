import os
from contextlib import redirect_stderr
import time

import spyctl.spyctl_lib as lib


def test_label_only_key_inp():
    test_str1 = "env"
    test_output1 = {"env": "*"}
    result1 = lib.label_input_to_dict(test_str1)
    assert result1 == test_output1

    test_str2 = "env, tier"
    test_output2 = {"env": "*", "tier": "*"}
    result2 = lib.label_input_to_dict(test_str2)
    assert result2 == test_output2


def test_label_set_inp():
    test_str1 = "env in (stage, prod)"
    test_output1 = {"env": ["stage", "prod"]}
    result1 = lib.label_input_to_dict(test_str1)
    assert result1 == test_output1

    test_str2 = "env in (stage, prod), tier"
    test_output2 = {"env": ["stage", "prod"], "tier": "*"}
    result2 = lib.label_input_to_dict(test_str2)
    assert result2 == test_output2


def test_label_eq_inp():
    test_str1 = "env=stage"
    test_output1 = {"env": "stage"}
    result1 = lib.label_input_to_dict(test_str1)
    assert result1 == test_output1

    test_str2 = "env=prod, tier=frontend"
    test_output2 = {"env": "prod", "tier": "frontend"}
    result2 = lib.label_input_to_dict(test_str2)
    assert result2 == test_output2

    test_str3 = "env=prod, tier=frontend, app"
    test_output3 = {"env": "prod", "tier": "frontend", "app": "*"}
    result3 = lib.label_input_to_dict(test_str3)
    assert result3 == test_output3

    test_str4 = "env=prod,tier=frontend,app"
    test_output4 = {"env": "prod", "tier": "frontend", "app": "*"}
    result4 = lib.label_input_to_dict(test_str4)
    assert result4 == test_output4


def test_label_list_inp():
    test_strs1 = ["env=stage"]
    test_output1 = {"env": "stage"}
    result1 = lib.label_input_to_dict(test_strs1)
    assert result1 == test_output1

    test_strs2 = ["env=prod, tier=frontend", "app in (web,db)"]
    test_output2 = {"env": "prod", "tier": "frontend", "app": ["web", "db"]}
    result2 = lib.label_input_to_dict(test_strs2)
    assert result2 == test_output2


def test_label_dict_inp():
    test_dict = {"env": "stage", "tier": "frontend", "app": ["web", "db"]}
    result = lib.label_input_to_dict(test_dict)
    assert result == test_dict


def test_notin_inp():
    err_log = "err.log"
    with open(err_log, "w") as stderr, redirect_stderr(stderr):
        test_str = "env notin (stage, prod)"
        result = lib.label_input_to_dict(test_str)
        assert result is None
    with open(err_log, "r") as stderr:
        err = stderr.readline()
        assert "notin not supported" in err

    os.remove(err_log)

    with open(err_log, "w") as stderr, redirect_stderr(stderr):
        test_str = "env notin (stage, prod), app in (web)"
        result = lib.label_input_to_dict(test_str)
        assert result is None
    with open(err_log, "r") as stderr:
        err = stderr.readline()
        assert "notin not supported" in err

    os.remove(err_log)


def test_timeinp():
    assert lib.time_inp("1677522138", cap_one_day=False) == 1677522138
    tests = (
        ("50s", lambda t: t - 50),
        ("4m", lambda t: t - 4 * 60),
        ("7hr", lambda t: t - 7 * 60 * 60),
        ("1d", lambda t: t - 24 * 60 * 60),
        ("3w", lambda t: t - 3 * 7 * 24 * 60 * 60),
        # ("Mon Feb 27 13:43:39 CST 2023", lambda _: 1677527019),
        ("2023/02/26 23:34:32", lambda _: 1677454472),
        ("01/26/2023", lambda _: 1674691200),
    )
    for inp, out in tests:
        t = time.time()
        assert abs(lib.time_inp(inp, cap_one_day=False) - out(t)) < 1
    capped_inp = lib.time_inp("09/16/2020", cap_one_day=True)
    one_day_ago = time.time() - 24 * 60 * 60
    assert abs(capped_inp - one_day_ago) < 1
