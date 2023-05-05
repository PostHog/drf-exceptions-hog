"""
Forked from https://github.com/encode/django-rest-framework
"""
import subprocess
import sys
from typing import Any, Dict

import pytest

PYTEST_ARGS: Dict[str, Any] = {
    "default": [],
}

PROJECT = ["exceptions_hog", "tests", "test_project"]

FLAKE8_ARGS = PROJECT

ISORT_ARGS = ["--check-only", "--diff"] + PROJECT

BLACK_ARGS = ["--check"] + PROJECT

MYPY_ARGS = PROJECT


def exit_on_failure(ret, message=None):
    if ret:
        sys.exit(ret)


def flake8_main(args):
    print("Running flake8 code linting")
    ret = subprocess.call(["flake8"] + args)
    print("❗️ flake8 failed" if ret else "✅ flake8 passed")
    return ret


def isort_main(args):
    print("Running isort code checking")
    ret = subprocess.call(["isort"] + args)

    if ret:
        print("❗️ isort failed: Fix by running `isort --recursive .`")
    else:
        print("✅ isort passed")

    return ret


def black_main(args):
    print("Running black format checking")
    ret = subprocess.call(["black"] + args)
    print("❗️ black failed") if ret else print("✅ black passed")
    return ret


def mypy_main(args):
    print("Running mypy typechecking")
    for proj in PROJECT:
        ret = subprocess.call(["mypy", "-p", proj])
        print("❗️ mypy failed for " + proj) if ret else print("✅ mypy passed for " + proj)
        if ret:
            return ret



def split_class_and_function(string):
    class_string, function_string = string.split(".", 1)
    return "%s and %s" % (class_string, function_string)


def is_function(string):
    # `True` if it looks like a test function is included in the string.
    return string.startswith("test_") or ".test_" in string


def is_class(string):
    # `True` if first character is uppercase - assume it's a class name.
    return string[0] == string[0].upper()


if __name__ == "__main__":
    try:
        sys.argv.remove("--no-lint")
    except ValueError:
        run_flake8 = True
        run_isort = True
        run_black = True
        run_mypy = True
    else:
        run_flake8 = False
        run_isort = False
        run_black = False
        run_mypy = False

    try:
        sys.argv.remove("--lint-only")
    except ValueError:
        run_tests = True
    else:
        run_tests = False

    if len(sys.argv) > 1:
        pytest_args = sys.argv[1:]
        first_arg = pytest_args[0]

        try:
            pytest_args.remove("--coverage")
        except ValueError:
            pass
        else:
            pytest_args = [
                "--cov",
                ".",
                "--cov-report",
                "xml",
            ] + pytest_args

        if first_arg.startswith("-"):
            # `runtests.py [flags]`
            pytest_args = ["tests"] + pytest_args
        elif is_class(first_arg) and is_function(first_arg):
            # `runtests.py TestCase.test_function [flags]`
            expression = split_class_and_function(first_arg)
            pytest_args = ["tests", "-k", expression] + pytest_args[1:]
        elif is_class(first_arg) or is_function(first_arg):
            # `runtests.py TestCase [flags]`
            # `runtests.py test_function [flags]`
            pytest_args = ["tests", "-k", pytest_args[0]] + pytest_args[1:]
    else:
        pytest_args = [""]

    if run_flake8:
        exit_on_failure(flake8_main(FLAKE8_ARGS))

    if run_isort:
        exit_on_failure(isort_main(ISORT_ARGS))

    if run_black:
        exit_on_failure(black_main(BLACK_ARGS))

    if run_mypy:
        exit_on_failure(mypy_main(MYPY_ARGS))

    if run_tests:
        exit_on_failure(pytest.main(pytest_args))
