from textual.app import App, ComposeResult
from textual.widgets import MarkdownViewer, Footer

class MarkdownExampleApp(App):
    BINDINGS = [("d", "toggle_dark", "Toggle dark mode"),
                ("q", "quit", "Quit")]

    def __init__(self, content: str):
        super().__init__()
        self.content = content

    def compose(self) -> ComposeResult:
        yield MarkdownViewer(self.content, show_table_of_contents=True)
        yield Footer()

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def action_quit(self) -> None:
        """An action to quit the app."""
        self.exit()


def view_md(report: str):
    app = MarkdownExampleApp(report)
    app.run()

