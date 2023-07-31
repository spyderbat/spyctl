import spyctl.spyctl_lib as lib
from typing import IO
import json


def handle_print_file(file: IO, list_output: bool):
    if list_output:
        data = [lib.load_file_for_api_test(file)]
    else:
        data = lib.load_file_for_api_test(file)
    data = json.dumps({"data": json.dumps(data)})
    print(data)
