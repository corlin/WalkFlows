"""Validation of scenario identifiers used in the upstream inventory."""
import re


def valid_scenario_name(name):
    return re.fullmatch(r"\d{3}_site\d{2}(?:_[A-Za-z0-9_]+)?", name) is not None
