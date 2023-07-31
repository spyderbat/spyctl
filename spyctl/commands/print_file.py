import spyctl.spyctl_lib as lib
from typing import IO
import json


def handle_print_file(file: IO):
    data = lib.load_file_for_api_test(file)
    print(json.dumps(data))
