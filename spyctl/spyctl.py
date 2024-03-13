#! /usr/bin/env python3

"""The main entry point for spyctl."""

# pylint: disable=broad-exception-caught

import inspect
import os
import time
from importlib import metadata
from pathlib import Path

import click

import spyctl.config.configs as cfgs
import spyctl.spyctl_lib as lib
from spyctl import api, cli
import spyctl.commands as cmds

MAIN_EPILOG = (
    "\b\n"
    'Use "spyctl <command> --help" for more information about a given '
    "command.\n"
    'Use "spyctl --version" for version information'
)

# ----------------------------------------------------------------- #
#                     Command Tree Entrypoint                       #
# ----------------------------------------------------------------- #


@click.group(cls=lib.CustomGroup, epilog=MAIN_EPILOG)
@click.help_option("-h", "--help", hidden=True)
@click.version_option(None, "-v", "--version", prog_name="Spyctl", hidden=True)
@click.option("--debug", is_flag=True, hidden=True)
def main(debug=False):
    """spyctl displays and controls resources within your Spyderbat
    environment
    """
    if debug:
        lib.set_debug()
    cfgs.load_config()
    version_check()


main.add_command(cmds.apply.apply)
main.add_command(cmds.create.create)
main.add_command(cmds.config.config)
main.add_command(cmds.delete.delete)
main.add_command(cmds.describe.describe)
main.add_command(cmds.diff.diff)
main.add_command(cmds.edit.edit)
main.add_command(cmds.export.export)
main.add_command(cmds.get.get)
main.add_command(cmds.logs.logs)
main.add_command(cmds.merge.merge)
main.add_command(cmds.print_file.print_file)
main.add_command(cmds.show_schema.show_schema)
main.add_command(cmds.spy_import.spy_import)
main.add_command(cmds.suppress.suppress)
main.add_command(cmds.test_notification.test_notification)
main.add_command(cmds.update.update)
main.add_command(cmds.validate.validate)

# ----------------------------------------------------------------- #
#                          Helper Functions                         #
# ----------------------------------------------------------------- #

V_CHECK_CACHE = Path.joinpath(cfgs.GLOBAL_CONFIG_DIR, ".v_check_cache")
V_CHECK_TIMEOUT = 14400  # 4 hours


def version_check():
    """
    Check the version of spyctl and compare it with the latest version
    available on PyPI. If a newer version is available, log a message with
    instructions on how to update.
    """
    check_version = False
    if not V_CHECK_CACHE.exists():
        check_version = True
    elif not V_CHECK_CACHE.is_file():
        os.rmdir(str(V_CHECK_CACHE))
        check_version = True
    else:
        with open(V_CHECK_CACHE, encoding="utf-8") as f:
            lines = f.readlines()
            if len(lines) == 0:
                check_version = True
            else:
                try:
                    last_check = float(lines[0])
                    now = time.time()
                    if last_check > now or now - last_check > V_CHECK_TIMEOUT:
                        check_version = True
                except Exception:
                    check_version = True

    if check_version:
        pypi_version = api.get_pypi_version()
        if not pypi_version:
            return
        local_version = get_local_version()
        if not local_version:
            cli.try_log("Unable to parse local version")
        if local_version != pypi_version:
            cli.try_log(
                f"[{lib.NOTICE_COLOR}notice{lib.COLOR_END}] A new release of"
                f" spyctl is available, {lib.WARNING_COLOR}{local_version}"
                f"{lib.COLOR_END} -> {lib.ADD_COLOR}{pypi_version}"
                f"{lib.COLOR_END}"
            )
            cli.try_log(
                f"[{lib.NOTICE_COLOR}notice{lib.COLOR_END}] To update, run: "
                f"{lib.ADD_COLOR}pip install spyctl -U{lib.COLOR_END}"
            )
    now = time.time()
    with open(V_CHECK_CACHE, "w", encoding="utf-8") as f:
        f.write(f"{now}")


def get_local_version():
    """
    Get the local version of the package.

    Returns:
        str: The version of the package if it is installed, None otherwise.

    Raises:
        RuntimeError: If the package is not installed.
    """
    frame = inspect.currentframe()
    f_back = frame.f_back if frame is not None else None
    f_globals = f_back.f_globals if f_back is not None else None
    del frame
    if f_globals is not None:
        package_name = f_globals.get("__name__")
        if package_name == "__main__":
            package_name = f_globals.get("__package__")
        if package_name:
            package_name = package_name.partition(".")[0]
        if package_name is not None:
            try:
                version = metadata.version(package_name)  # type: ignore
            except metadata.PackageNotFoundError:  # type: ignore
                raise RuntimeError(
                    f"{package_name!r} is not installed. Try passing"
                    " 'package_name' instead."
                ) from None
            return version
    return None


if __name__ == "__main__":
    main()
