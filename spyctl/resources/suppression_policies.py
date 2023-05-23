from typing import Dict
import spyctl.spyctl_lib as lib


def create_suppression_policy(
    trace_summary: Dict, include_users: bool = False
) -> Dict:
    pol = SuppressionPolicy(trace_summary)
    return pol.make_suppresion_policy(include_users)


class SuppressionPolicy:
    def __init__(self, trace_summary: Dict) -> None:
        self.trace_summary = trace_summary
        self.trace_selector = None
        self.user_selector = None

    def make_suppresion_policy(self, include_users=False) -> Dict:
        rv = {
            lib.API_FIELD: lib.API_VERSION,
            lib.KIND_FIELD: lib.POL_KIND,
            lib.METADATA_FIELD: {
                lib.NAME_FIELD: self.__build_name(),
                lib.TYPE_FIELD: lib.POL_TYPE_TRACE,
                lib.LATEST_TIMESTAMP_FIELD: self.trace_summary["last_seen"],
            },
            lib.SPEC_FIELD: {
                lib.TRACE_SELECTOR_FIELD: self.__build_trace_selector(),
                lib.USER_SELECTOR_FIELD: None,
                lib.ALLOWED_FLAGS_FIELD: self.__build_flags(),
            },
        }
        if not include_users:
            del rv[lib.SPEC_FIELD][lib.USER_SELECTOR_FIELD]
        else:
            rv[lib.SPEC_FIELD][
                lib.USER_SELECTOR_FIELD
            ] = self.__build_user_selector()
        return rv

    def __build_name(self) -> str:
        trig_ancestors = self.trace_summary[lib.TRACE_SELECTOR_FIELD][
            lib.TRIGGER_ANCESTORS_FIELD
        ]
        return f"Suppression Policy for {trig_ancestors}"

    def __build_flags(self) -> Dict:
        flags = self.trace_summary.get("flag")
        if flags:
            flags = flags.get(lib.FLAGS_FIELD)
        else:
            flags = self.trace_summary.get(lib.FLAGS_FIELD)
        return [{lib.FLAG_CLASS: f[lib.FLAG_CLASS]} for f in flags]

    def __build_trace_selector(self) -> Dict:
        if self.trace_selector:
            return self.trace_selector
        rv = {}
        trigger_class = self.trace_summary[lib.TRACE_SELECTOR_FIELD].get(
            lib.TRIGGER_CLASS_FIELD
        )
        if not trigger_class:
            trigger_class = self.trace_summary[lib.TRACE_SELECTOR_FIELD].get(
                "trigger_class"
            )
        if trigger_class:
            rv[lib.TRIGGER_CLASS_FIELD] = trigger_class
        trigger_ancestors = self.trace_summary[lib.TRACE_SELECTOR_FIELD].get(
            lib.TRIGGER_ANCESTORS_FIELD
        )
        if not trigger_ancestors:
            trigger_ancestors = self.trace_summary[
                lib.TRACE_SELECTOR_FIELD
            ].get("trigger_ancestors")
        if trigger_ancestors:
            rv[lib.TRIGGER_ANCESTORS_FIELD] = trigger_ancestors
        return rv

    def __build_user_selector(self) -> Dict:
        if self.user_selector:
            return self.user_selector
        rv = {}
        users = self.trace_summary[lib.USER_SELECTOR_FIELD].get(
            lib.USERS_FIELD
        )
        if not users:
            users = self.trace_summary[lib.USER_SELECTOR_FIELD].get(
                "whitelist"
            )
        if users:
            rv["users"] = users
        return rv
