from __future__ import annotations

from typing  import Protocol, Optional
import importlib
import pkgutil
import yaml
from jinja2 import Environment, PackageLoader

_inventory: dict = {}
def get_inventory():
    global _inventory
    if not _inventory:
        data = pkgutil.get_data("app", "reports/inventory.yaml")
        _inventory = yaml.safe_load(data)
    return _inventory

def get_report_spec(report: str):
    reports = get_inventory()["reports"]
    spec = [r for r in reports if r["id"] == report]
    if not spec:
        raise ValueError(f"Report {report} not found")
    return spec[0]

def get_template(report: str, format: str):
    environment = Environment(
        loader = PackageLoader("app.reports", "templates")
    )
    spec = get_report_spec(report)
    template = spec["templates"][format]
    return environment.get_template(template)

def get_reporter(report: str) -> Reporter:
    spec = get_report_spec(report)
    reporter_str = spec["reporter"]
    mod_str, cls_str = reporter_str.rsplit(".", 1)
    mod = importlib.import_module(mod_str)
    cls = getattr(mod, cls_str)
    return cls()

def validate_args(report: str, args: dict[str, str|float|int|bool]):
    pass


class Reporter(Protocol):
    def collector(
            self,
            args: dict[str, str|float|int|bool],
            org_uid: str,
            api_key: str,
            api_url: str) -> list:
        ...

    def processor(
            self,
            data: list,
            args: dict[str, str|float|int|bool],
            mock: Optional[dict]=None,
            format: Optional[str]="md") -> dict:
        ...

def make_report(
    report: str,
    args: dict[str, str|float|int|bool],
    org_uid: str,
    api_key: str,
    api_url: str,
    mock: dict = {},
    format: str = "md") -> str:
        reporter = get_reporter(report)
        template = get_template(report, format)
        data = reporter.collector(args, org_uid, api_key, api_url)
        context = reporter.processor(data, args, mock, format)
        report = template.render(context)
        return report
