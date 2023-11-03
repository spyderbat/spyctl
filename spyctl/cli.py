import curses
import curses.ascii
import curses.textpad as textpad
import json
import os
import re
import sys
import time
from collections import namedtuple
from collections.abc import Iterable, Sequence
from pathlib import Path
from pydoc import pager, pipepager
from typing import Callable, Dict, List, Any, Tuple, Optional
from typing_extensions import Literal
from urwid.listbox import ListWalker
from urwid.widget.constants import Align, WrapMode
from urwid.widget.widget import Widget
from urwid.command_map import Command

import yaml
import urwid as u

import spyctl.spyctl_lib as lib

yaml.Dumper.ignore_aliases = lambda *args: True

WARNING_MSG = "is_warning"
WARNING_COLOR = lib.WARNING_COLOR
COLOR_END = lib.COLOR_END


def try_log(*args, **kwargs):
    lib.try_log(*args, **kwargs)


def try_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
        sys.stdout.flush()
    except BrokenPipeError:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        sys.exit(1)


def unsupported_output_msg(output: str) -> str:
    return f"'--output {output}' is not supported for this command."


YES_OPTION = False


def set_yes_option():
    global YES_OPTION
    YES_OPTION = True


def query_yes_no(question, default="yes", ignore_yes_option=False):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
            It must be "yes" (the default), "no" or None (meaning
            an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        if YES_OPTION and not ignore_yes_option:
            return True
        sys.stderr.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == "":
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stderr.write(
                "Please respond with 'yes' or 'no' " "(or 'y' or 'n').\n"
            )


def notice(notice_msg):
    """Notify the user of something, wait for input

    "notice_msg" is a string that is presented to the user.
    """
    if YES_OPTION:
        return
    prompt = " [ok] "
    sys.stderr.write(notice_msg + prompt)
    input()


def show(
    obj,
    output,
    alternative_outputs: Dict[str, Callable] = {},
    dest=lib.OUTPUT_DEST_STDOUT,
    output_fn=None,
    ndjson=False,
):
    """Display or save python object

    Args:
        obj (any): python object to be displayed or saved
        output (str): the format of the output
        alternative_outputs (Dict[str, Callable], optional): A
            dictionary of formats to callables for custom outputs.
            Defaults to {}. Callable must return a string.
        dest (str, optional): Destination of the output. Defaults to
            lib.OUTPUT_DEST_STDOUT.
        output_fn (str, optional): Filename if outputting to a file.
            Defaults to None.
        ndjson (bool, optional): If output is json, output the json on a
            single line. Defaults to False
    """
    out_data = None
    if output == lib.OUTPUT_YAML:
        out_data = yaml.dump(obj, sort_keys=False)
        if output_fn:
            output_fn += ".yaml"
    elif output == lib.OUTPUT_JSON:
        if ndjson:
            if _seq_but_not_str(obj):
                out_data = []
                for item in obj:
                    out_data.append(json.dumps(item))
                out_data = "\n".join(out_data)
            else:
                out_data = json.dumps(obj)
        else:
            out_data = json.dumps(obj, sort_keys=False, indent=2)
        if output_fn:
            output_fn += ".json"
    elif output == lib.OUTPUT_RAW:
        out_data = obj
    elif output in alternative_outputs:
        out_data = alternative_outputs[output](obj)
    else:
        try_log(unsupported_output_msg(output), is_warning=True)
    if out_data:
        if dest == lib.OUTPUT_DEST_FILE:
            try:
                out_file = Path(output_fn)
                out_file.write_text(out_data)
                try_log(f"Saved output to {output_fn}")
            except Exception:
                try_log(
                    f"Unable to write output to {output_fn}", is_warning=True
                )
                return
        elif dest == lib.OUTPUT_DEST_PAGER:
            output_to_pager(out_data)
        else:
            try_print(out_data)


def read_stdin():
    if sys.stdin.isatty():
        return ""
    return sys.stdin.read().strip()


def get_open_input(string: str):
    if string == "-":
        return read_stdin().strip('"')
    if os.path.exists(string):
        with open(string, "r") as f:
            return f.read().strip().strip('"')
    return string


def handle_list(list_string: str, obj_to_str=None) -> List[str]:
    try:
        objs = None
        try:
            objs = json.loads(list_string)
        except json.JSONDecodeError:
            objs = yaml.load(list_string, yaml.Loader)
            if isinstance(objs, str):
                raise ValueError
        if obj_to_str is not None:
            ret = []
            if isinstance(objs, dict):
                objs = [obj for obj in objs.values()]
            for obj in objs:
                string = obj_to_str(obj)
                if isinstance(string, list):
                    ret.extend(string)
                else:
                    ret.append(string)
            return ret
        return objs
    except Exception:
        return [s.strip().strip('"') for s in list_string.split(",")]


def time_input(args):
    if args.within:
        tup = args.within, int(time.time())
        return tup
    elif args.time_range:
        if args.time_range[1] < args.time_range[0]:
            err_exit("start time was before end time")
        return tuple(args.time_range)
    else:
        t = args.time if args.time else time.time()
        return t, t


def err_exit(message: str, exception: Exception = None):
    lib.err_exit(message, exception)


def output_to_pager(text: str):
    try:
        pipepager(text, cmd="less -R")
    except Exception:
        text = strip_color(text)
        pager(text)


ANSI_ESCAPE = re.compile(
    r"""
    \x1B  # ESC
    (?:   # 7-bit C1 Fe (except CSI)
        [@-Z\\-_]
    |     # or [ for CSI, followed by a control sequence
        \[
        [0-?]*  # Parameter bytes
        [ -/]*  # Intermediate bytes
        [@-~]   # Final byte
    )
    """,
    re.VERBOSE,
)


def strip_color(text: str):
    rv = ANSI_ESCAPE.sub("", text)
    return rv


def _seq_but_not_str(obj):
    return isinstance(obj, Sequence) and not isinstance(
        obj, (str, bytes, bytearray)
    )


menu_item = namedtuple(
    "menu_item", ["option_txt", "description", "return_val"]
)


def selection_menu(title: str, menu_items: List[menu_item], selected_option=0):
    return curses.wrapper(__selection_menu, title, menu_items, selected_option)


def __selection_menu(
    stdscr: curses.window, title, menu_items: List[menu_item], selected_option
):
    if not selected_option:
        selected_option = 0
    # Set up the screen
    curses.curs_set(0)
    stdscr.clear()
    stdscr.addstr(title, curses.A_BOLD)
    stdscr.refresh()
    y, x = stdscr.getmaxyx()
    menu = curses.newwin(y - 1, x, 1, 0)
    menu.keypad(True)

    # Initialize variables
    key = 0

    while key != ord("q"):  # 'q' key to quit
        menu.clear()

        # Display the menu
        for i, item in enumerate(menu_items):
            if i == selected_option:
                menu.addstr(i, 0, f"> {item.option_txt}", curses.A_BOLD)
            else:
                menu.addstr(i, 0, f"  {item.option_txt}")

        # Display the description of the selected option
        _, cols = menu.getmaxyx()
        menu.addstr(len(menu_items), 0, "-" * cols)
        menu.addstr(
            len(menu_items) + 1, 1, menu_items[selected_option].description
        )

        # Refresh the screen
        menu.refresh()

        key = menu.getch()

        # Handle arrow key presses to navigate the menu
        if key == curses.KEY_DOWN and selected_option < len(menu_items) - 1:
            selected_option += 1
        elif key == curses.KEY_UP and selected_option > 0:
            selected_option -= 1
        elif key == curses.KEY_UP:
            selected_option = len(menu_items) - 1
        elif key == curses.KEY_DOWN:
            selected_option = 0
        elif key == curses.KEY_ENTER or key == 10 or key == 13:
            return menu_items[selected_option].return_val


def input_window(
    prompt,
    description=None,
    existing_data="",
    validator: callable = None,
    error_msg=None,
    show_error_msg=False,
):
    if show_error_msg and error_msg:
        e_msg = error_msg
    else:
        e_msg = None
    while True:
        rv = curses.wrapper(
            __input_window, prompt, description, existing_data, e_msg
        )
        if rv is not None and validator:
            if not validator(rv):
                show_error_msg = True
                e_msg = error_msg
                continue
        break
    return rv


class SingleLineTextBox(textpad.Textbox):
    def do_command(self, ch):
        "Process a single editing command."
        self._update_max_yx()
        (y, x) = self.win.getyx()
        self.lastcmd = ch
        if curses.ascii.isprint(ch):
            if y < self.maxy or x < self.maxx:
                self._insert_printable_char(ch)
        elif ch == curses.ascii.SOH:  # ^a
            self.win.move(y, 0)
        elif ch in (
            curses.ascii.STX,
            curses.KEY_LEFT,
            curses.ascii.BS,
            curses.KEY_BACKSPACE,
        ):
            if x > 0:
                self.win.move(y, x - 1)
            elif y == 0:
                pass
            elif self.stripspaces:
                self.win.move(y - 1, self._end_of_line(y - 1))
            else:
                self.win.move(y - 1, self.maxx)
            if ch in (curses.ascii.BS, curses.KEY_BACKSPACE):
                self.win.delch()
        elif ch == curses.ascii.EOT:  # ^d
            self.win.delch()
        elif ch == curses.ascii.ENQ:  # ^e
            if self.stripspaces:
                self.win.move(y, self._end_of_line(y))
            else:
                self.win.move(y, self.maxx)
        elif ch in (curses.ascii.ACK, curses.KEY_RIGHT):  # ^f
            if x < self.maxx and x < self._get_end_of_line(y):
                self.win.move(y, x + 1)
            elif y == self.maxy:
                old_x = x
                self.win.refresh()
                (y, x) = self.win.getyx()
                if x != old_x:
                    self.win.move(y, x + 1)
                pass
            else:
                self.win.move(y + 1, 0)
        elif ch == curses.ascii.BEL:  # ^g
            return 0
        elif ch == curses.ascii.NL:  # ^j
            if self.maxy == 0:
                return 0
            elif y < self.maxy:
                self.win.move(y + 1, 0)
        elif ch == curses.ascii.VT:  # ^k
            if x == 0 and self._end_of_line(y) == 0:
                self.win.deleteln()
            else:
                # first undo the effect of self._end_of_line
                self.win.move(y, x)
                self.win.clrtoeol()
        elif ch == curses.ascii.FF:  # ^l
            self.win.refresh()
        elif ch in (curses.ascii.SO, curses.KEY_DOWN):  # ^n
            if y < self.maxy:
                self.win.move(y + 1, x)
                if x > self._end_of_line(y + 1):
                    self.win.move(y + 1, self._end_of_line(y + 1))
        elif ch == curses.ascii.SI:  # ^o
            self.win.insertln()
        elif ch in (curses.ascii.DLE, curses.KEY_UP):  # ^p
            if y > 0:
                self.win.move(y - 1, x)
                if x > self._end_of_line(y - 1):
                    self.win.move(y - 1, self._end_of_line(y - 1))
        return 1

    def _get_end_of_line(self, y):
        """Go to the location of the first blank on the given line,
        returning the index of the last non-blank character."""
        last = self.maxx
        while True:
            if curses.ascii.ascii(self.win.inch(y, last)) != curses.ascii.SP:
                last = min(self.maxx, last + 1)
                break
            elif last == 0:
                break
            last = last - 1
        return last


def __input_window(
    stdscr: curses.window, prompt, description, existing_data, error_msg
):
    curses.curs_set(1)
    stdscr.clear()
    stdscr.refresh()
    _, x = stdscr.getmaxyx()
    if description and error_msg:
        h = 5
        err_y = 2
        text_y = 3
    elif description or error_msg:
        h = 4
        err_y = 1
        text_y = 2
    else:
        h = 3
        text_y = 1
    win = curses.newwin(h, x)
    win.border(0)
    if description:
        win.addstr(1, 1, description)
    if error_msg:
        win.addstr(err_y, 1, error_msg)
    prompt = prompt + ": "
    win.addstr(text_y, 1, prompt)
    text_win = win.subwin(1, x - (2 + len(prompt)), text_y, len(prompt) + 1)
    if existing_data:
        text_win.addstr(existing_data)
    win.refresh()
    stdscr.refresh()
    box = SingleLineTextBox(text_win, insert_mode=True)
    box.stripspaces = 0
    while True:
        ch = text_win.getch()
        if ch == 27:
            break
        if not ch:
            continue
        if not box.do_command(ch):
            break
        text_win.refresh()
    rv = box.gather().strip().replace("\n", "")
    return rv


def __esc_is_terminate(key):
    if key == 27:
        return 7
    return key


URWID_PALLET = {
    ("bg", "white", "black"),
    ("header", "white", "black"),
    ("item", "white", "black"),
    ("item_selected", "white", "dark gray"),
    ("footer", "white, bold", "dark red"),
}


def selection_menu_v2(
    title: str,
    menu_items: List[menu_item],
    selected_option: int,
    footer: str,
    selection_callback: Callable,
) -> u.Frame:
    def selections_height(max_rows: int):
        two_thirds = int((2 / 3) * max_rows)
        if len(menu_items) < two_thirds:
            return len(menu_items)
        else:
            return two_thirds

    list_view = ListView()
    desc_view = DescriptionView()
    u.connect_signal(list_view, "show_description", desc_view.set_description)
    u.connect_signal(list_view, "selection", selection_callback)
    header = u.AttrMap(u.Text(title), "header")
    footer = u.AttrWrap(u.Text(footer), "footer")
    col_rows = u.raw_display.Screen().get_cols_rows()
    h = col_rows[0] - 2
    f1 = u.BoxAdapter(list_view, height=selections_height(h))
    f2 = u.Filler(desc_view, valign="top")
    c_list = u.Padding(f1, left=1)
    c_details = u.Padding(f2, left=1)
    divider = u.Divider("-")
    sections = u.Pile(
        [
            ("pack", c_list),
            ("pack", divider),
            ("weight", 30, c_details),
        ]
    )
    frame = u.AttrMap(
        u.Frame(header=header, body=sections, footer=footer), "bg"
    )
    list_view.set_data(menu_items, selected_option)
    return frame


def extended_selection_menu(
    title: str,
    menu_items: List[menu_item],
    footer: str,
    selection_callback: Callable,
):
    list_view = ListView()
    u.connect_signal(list_view, "selection", selection_callback)
    header = u.AttrMap(u.Text(title), "header")
    footer = u.AttrWrap(u.Text(footer), "footer")
    col_rows = u.raw_display.Screen().get_cols_rows()
    h = col_rows[0] - 2
    f1 = u.Filler(list_view, valign="top", height=h)
    c_list = u.Padding(f1, left=1)
    frame = u.AttrMap(u.Frame(header=header, body=c_list, footer=footer), "bg")
    list_view.set_data(menu_items)
    return frame


def urwid_prompt(
    prompt: str,
    description: str,
    confirm_callback: Callable,
    cancel_callback: Callable,
    old_data: str = "",
    validator: Callable = None,
):
    return Prompt(
        prompt,
        description,
        confirm_callback,
        cancel_callback,
        old_data,
        validator,
    )


def urwid_multi_line_prompt(
    prompt: str,
    confirm_callback: Callable,
    cancel_callback: Callable,
    old_data: str = "",
    is_yaml: bool = False,
    validator: Callable = None,
):
    return MultiLineEditBox(
        prompt, old_data, confirm_callback, cancel_callback, is_yaml, validator
    )


def urwid_pager(data: str, footer, on_close: Callable = None):
    data = data.replace("\t", " " * TAB_WIDTH)
    footer = u.AttrWrap(u.Text(footer), "footer")
    pager_view = Pager(on_close)
    pager_view.set_data(data)
    frame = u.AttrMap(u.Frame(pager_view, footer=footer), "bg")
    return frame


def urwid_query_yes_no(
    query: str,
    response_callback: Callable,
    cancel_callback: Callable,
    default="yes",
):
    frame = QueryYesNo(query, default, response_callback, cancel_callback)
    return frame


class QueryYesNo(u.WidgetWrap):
    def __init__(
        self,
        query,
        default,
        response_callback,
        cancel_callback,
    ):
        u.register_signal(self.__class__, ["response", "cancel"])
        u.connect_signal(self, "response", response_callback)
        u.connect_signal(self, "cancel", cancel_callback)
        self.default = default
        self.valid_confirm = {
            "yes": True,
            "y": True,
            "ye": True,
        }
        self.valid_cancel = {
            "no": False,
            "n": False,
        }
        self.valid = {**self.valid_confirm, **self.valid_cancel}
        if default is None:
            prompt = "[y/n]"
        elif default == "yes":
            prompt = "[Y/n]"
        elif default == "no":
            prompt = "[y/N]"
        else:
            raise ValueError("invalid default answer: '%s'" % default)
        self.edit_box = EditBox(prompt, "", self.validate_confirm, self.cancel)
        query = u.Padding(u.AttrMap(u.Text(query), "item"), left=1)
        divider = u.Divider("-")
        box = u.Padding(self.edit_box, left=1)
        divider2 = u.Divider("_")
        self.error_box = u.Text("")
        error = u.Padding(
            u.Filler(u.AttrMap(self.error_box, "item"), valign="top"), left=1
        )
        sections = u.Pile(
            [
                ("pack", query),
                ("pack", divider),
                ("pack", box),
                ("pack", divider2),
                ("weight", 1, error),
            ]
        )
        footer = u.AttrWrap(
            u.Text("Esc to cancel, Enter to confirm"), "footer"
        )
        self.frame = u.AttrMap(u.Frame(sections, footer=footer), "bg")
        super().__init__(self.frame)

    def validate_confirm(self, text: str):
        choice = text.lower()
        if self.default is not None and choice == "":
            choice = self.default
        elif choice not in self.valid:
            self.error_box.set_text(
                "Please respond with 'yes' or 'no' " "(or 'y' or 'n').\n"
            )
            self.edit_box.box.set_edit_text("")
            return
        if choice in self.valid_confirm:
            resp = True
        else:
            resp = False
        u.emit_signal(self, "response", resp)

    def cancel(self, _):
        u.emit_signal(self, "cancel", True)


class MyEdit(u.Edit):
    signals = ["change", "postchange", "cancel", "confirm", "validation_error"]

    def __init__(
        self,
        caption="",
        edit_text: str = "",
        multiline: bool = False,
        align=Align.LEFT,
        wrap=WrapMode.SPACE,
        allow_tab: bool = False,
        edit_pos: int = None,
        layout=None,
        mask: str = None,
        validator: Callable = None,
    ) -> None:
        self.old_text = edit_text
        self.validator = validator
        super().__init__(
            caption,
            edit_text,
            multiline,
            align,
            wrap,
            allow_tab,
            edit_pos,
            layout,
            mask,
        )

    def keypress(self, size, key):
        if key == "enter":
            if self.validator:
                error_msg = self.validator(self.get_edit_text())
                if error_msg:
                    u.emit_signal(self, "validation_error", error_msg)
                    return
            u.emit_signal(self, "confirm", self.get_edit_text())
        elif key == "esc":
            u.emit_signal(self, "cancel", self.old_text)
        else:
            super().keypress(size, key)


class MyMultiLineEdit(u.Edit):
    signals = ["change", "postchange", "cancel", "confirm", "validation_error"]

    def __init__(
        self,
        caption="",
        edit_text: str = "",
        multiline: bool = False,
        align=Align.LEFT,
        wrap=WrapMode.SPACE,
        allow_tab: bool = False,
        edit_pos: int = None,
        layout=None,
        mask: str = None,
        is_yaml: bool = False,
        validator: Callable = None,
    ) -> None:
        self.old_text = edit_text
        self.is_yaml = is_yaml
        self.validator = validator
        super().__init__(
            caption,
            edit_text,
            multiline,
            align,
            wrap,
            allow_tab,
            edit_pos,
            layout,
            mask,
        )

    def keypress(self, size, key):
        if key == "ctrl x":
            if self.validator:
                error_msg = self.validator(self.get_edit_text())
                if error_msg:
                    u.emit_signal(self, "validation_error", error_msg)
                    return
            u.emit_signal(self, "confirm", self.get_edit_text())
        if key == "esc":
            u.emit_signal(self, "cancel", self.old_text)
        if self.is_yaml and key == "tab":
            key = " " * (
                YAML_TAB_WIDTH
                - (self.__distance_from_line_start() % YAML_TAB_WIDTH)
            )
            self.insert_text(key)
            return None
        else:
            super().keypress(size, key)

    def __distance_from_line_start(self) -> int:
        text_slice = self.get_edit_text()[: self.edit_pos]
        lines = text_slice.split("\n")
        return len(lines[-1])


class EditBox(u.WidgetWrap):
    def __init__(
        self,
        prompt,
        old_text,
        confirm_callback,
        cancel_callback,
        validator=None,
        validator_callback=None,
    ):
        u.register_signal(self.__class__, ["confirm", "cancel"])
        self.old_text = old_text
        self.prompt = prompt
        self.box = MyEdit(f"{prompt}: ", old_text, validator=validator)
        self.validator = validator
        u.connect_signal(self.box, "confirm", confirm_callback)
        u.connect_signal(self.box, "cancel", cancel_callback)
        if self.validator:
            if not validator_callback:
                raise ValueError(
                    "validator_callback must be set it validator is set"
                )
            u.connect_signal(self.box, "validation_error", validator_callback)
        super().__init__(self.box)


TAB_WIDTH = 4
YAML_TAB_WIDTH = 2


class Prompt(u.WidgetWrap):
    def __init__(
        self,
        prompt: str,
        description: str,
        confirm_callback: Callable,
        cancel_callback: Callable,
        old_data: str = "",
        validator: Callable = None,
        clear_text_on_error=False,
    ):
        if old_data is None:
            old_data = ""
        self.clear_text_on_error = clear_text_on_error
        # prompt = u.AttrMap(u.Text(f"{prompt}: "), "item")
        description = u.AttrMap(u.Text(description), "item")
        self.edit_box = EditBox(
            prompt,
            old_data,
            confirm_callback,
            cancel_callback,
            validator,
            self.validation_error,
        )
        edit_box = u.Padding(self.edit_box, left=1)
        description = u.Padding(description, left=1)
        footer = u.AttrWrap(
            u.Text("Esc to cancel, Enter to confirm"), "footer"
        )
        divider = u.Divider("-")
        divider2 = u.Divider("_")
        self.error_box = u.Text("")
        error = u.Padding(
            u.Filler(u.AttrMap(self.error_box, "item"), valign="top"), left=1
        )
        sections = u.Pile(
            [
                ("pack", description),
                ("pack", divider),
                ("pack", edit_box),
                ("pack", divider2),
                ("weight", 1, error),
            ]
        )
        frame = u.AttrMap(u.Frame(body=sections, footer=footer), "bg")
        super().__init__(frame)

    def validation_error(self, error_msg: str):
        if error_msg:
            error_msg = error_msg.replace("\t", " " * TAB_WIDTH)
            self.error_box.set_text(error_msg)
        if self.clear_text_on_error:
            self.edit_box.box.set_edit_text("")


class MultiLineEditBox(u.WidgetWrap):
    def __init__(
        self,
        prompt,
        old_text: str,
        confirm_callback,
        cancel_callback,
        is_yaml=False,
        validator=False,
        clear_text_on_error=False,
    ):
        if old_text is None:
            old_text = ""
        self.clear_text_on_error = clear_text_on_error
        u.register_signal(self.__class__, ["confirm", "cancel"])
        old_text = old_text.replace("\t", " " * TAB_WIDTH)
        prompt = u.Padding(u.AttrMap(u.Text(prompt), "item"), left=1)
        self.edit_box = MyMultiLineEdit(
            "",
            old_text,
            multiline=True,
            allow_tab=True,
            is_yaml=is_yaml,
            validator=validator,
        )
        u.connect_signal(self.edit_box, "confirm", confirm_callback)
        u.connect_signal(self.edit_box, "cancel", cancel_callback)
        u.connect_signal(
            self.edit_box, "validation_error", self.validation_error
        )
        edit_box = u.Padding(u.Filler(self.edit_box, valign="top"), left=1)
        footer = u.AttrWrap(
            u.Text("Esc to cancel, Ctrl+x to confirm"), "footer"
        )
        divider = u.Divider("-")
        divider2 = u.Divider("_")
        self.error_box = u.Text("")
        error = u.Padding(u.AttrMap(self.error_box, "item"), left=1)
        sections = u.Pile(
            [
                ("pack", prompt),
                ("pack", divider),
                ("weight", 1, edit_box),
                ("pack", divider2),
                ("pack", error),
            ]
        )
        frame = u.AttrMap(u.Frame(body=sections, footer=footer), "bg")
        super().__init__(frame)

    def validation_error(self, error_msg: str):
        if error_msg:
            error_msg = error_msg.replace("\t", " " * TAB_WIDTH)
            self.error_box.set_text(error_msg)
        if self.clear_text_on_error:
            self.edit_box.set_edit_text("")


class PagerListBox(u.ListBox):
    signals = ["modified", "on_close"]

    def __init__(self, body: ListWalker):
        super().__init__(body)

    def keypress(self, size: Tuple[int, int], key: str) -> Optional[str]:
        if key == "q":
            u.emit_signal(self, "on_close")
        else:
            return super().keypress(size, key)


class Pager(u.WidgetWrap):
    def __init__(self, on_close: Callable = None):
        self.walker = u.SimpleListWalker([])
        self.box = PagerListBox(self.walker)
        if on_close:
            u.connect_signal(self.box, "on_close", on_close)
        super().__init__(self.box)

    def set_data(self, data: str):
        self.walker.extend([u.Text(line) for line in data.splitlines()])
        self.walker.set_focus(0)


class ListItem(u.WidgetWrap):
    def __init__(self, item: menu_item):
        u.register_signal(self.__class__, ["selection"])
        self.content = item

        t = u.AttrWrap(u.Text(item.option_txt), "item", "item_selected")

        u.WidgetWrap.__init__(self, t)

    def selectable(self):
        return True

    def keypress(self, size, key):
        if key == "enter":
            u.emit_signal(self, "selection", self.content.return_val)
        else:
            return key


class MyListBox(u.ListBox):
    def keypress(self, size: Tuple[int, int], key: str) -> Optional[str]:
        """Move selection through the list elements scrolling when
        necessary. Keystrokes are first passed to widget in focus
        in case that widget can handle them.

        Keystrokes handled by this widget are:
         'up'        up one line (or widget)
         'down'      down one line (or widget)
         'page up'   move cursor up one listbox length (or widget)
         'page down' move cursor down one listbox length (or widget)
        """
        (maxcol, maxrow) = size

        if self.set_focus_pending or self.set_focus_valign_pending:
            self._set_focus_complete((maxcol, maxrow), focus=True)

        focus_widget, pos = self._body.get_focus()
        if focus_widget is None:  # empty listbox, can't do anything
            return key

        if focus_widget.selectable():
            key = focus_widget.keypress((maxcol,), key)
            if key is None:
                self.make_cursor_visible((maxcol, maxrow))
                return None

        def actual_key(unhandled):
            if unhandled:
                return key
            return None

        # pass off the heavy lifting
        if self._command_map[key] == Command.UP:
            _, pos = self.get_focus()
            if pos > 0:
                return actual_key(self._keypress_up((maxcol, maxrow)))
            else:
                self.set_focus(len(self._body) - 1)

        if self._command_map[key] == Command.DOWN:
            _, pos = self.get_focus()
            if pos < (len(self._body) - 1):
                return actual_key(self._keypress_down((maxcol, maxrow)))
            else:
                self.set_focus(0)

        if self._command_map[key] == Command.PAGE_UP:
            return actual_key(self._keypress_page_up((maxcol, maxrow)))

        if self._command_map[key] == Command.PAGE_DOWN:
            return actual_key(self._keypress_page_down((maxcol, maxrow)))

        if self._command_map[key] == Command.MAX_LEFT:
            return actual_key(self._keypress_max_left((maxcol, maxrow)))

        if self._command_map[key] == Command.MAX_RIGHT:
            return actual_key(self._keypress_max_right((maxcol, maxrow)))

        return key


class ListView(u.WidgetWrap):
    def __init__(self):
        u.register_signal(
            self.__class__, ["show_description", "selection", "show_error"]
        )

        self.walker = u.SimpleFocusListWalker([])

        lb = MyListBox(self.walker)

        u.WidgetWrap.__init__(self, lb)

    def modified(self):
        focus_w, _ = self.walker.get_focus()
        item: menu_item = focus_w.content
        u.emit_signal(self, "show_description", item)

    def selection(self, return_val: Any):
        u.emit_signal(self, "selection", return_val)

    def set_data(self, menu_items: List[menu_item], selected_item=0):
        menu_item_widgets = [ListItem(mi) for mi in menu_items]

        u.disconnect_signal(self.walker, "modified", self.modified)

        while len(self.walker) > 0:
            self.walker.pop()

        self.walker.extend(menu_item_widgets)

        u.connect_signal(self.walker, "modified", self.modified)
        for item in self.walker:
            u.connect_signal(item, "selection", self.selection)

        self.walker.set_focus(selected_item)


class DescriptionView(u.WidgetWrap):
    def __init__(self):
        t = u.Text("")
        u.WidgetWrap.__init__(self, t)

    def set_description(self, item: menu_item):
        self._w.set_text(item.description)
