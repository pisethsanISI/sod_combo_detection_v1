"""Resolving a user's effective SAP T-code access from role/composite-role
assignment data. Same resolution logic as the main SOD_Detection project
(composite roles hold no T-codes of their own in SAP -- they're bundles of
"single roles", and must be expanded before any T-code lookup) -- kept
standalone here so this project has no filesystem/import dependency on
SOD_Detection.
"""

import csv
from collections import defaultdict

ROLE_TCODES_COLUMNS = {"role_id", "tcode"}
USER_ROLES_COLUMNS = {"user_id", "role_id"}
COMPOSITE_ROLES_COLUMNS = {"composite_role_id", "single_role_id"}


def _require_columns(fieldnames, required, path):
    """Raise a clear, actionable error if a CSV is missing a required
    column -- instead of letting row["missing_key"] blow up as a bare
    KeyError deep inside the row loop, pointing at neither the file nor
    what's actually wrong with it.
    """
    found = set(fieldnames or [])
    missing = required - found
    if missing:
        found_desc = sorted(found) if found else "no columns -- is the file empty?"
        raise ValueError(f"{path}: missing required column(s) {sorted(missing)} (found: {found_desc})")


def load_role_tcodes(path):
    """Load a role_id,tcode CSV into {role_id: {tcode, ...}}."""
    role_tcodes = defaultdict(set)
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        _require_columns(reader.fieldnames, ROLE_TCODES_COLUMNS, path)
        for row in reader:
            role_tcodes[row["role_id"]].add(row["tcode"].strip().upper())
    return role_tcodes


def load_composite_roles(path):
    """Load a composite_role_id,single_role_id CSV into
    {composite_role_id: {single_role_id, ...}}."""
    composite_children = defaultdict(set)
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        _require_columns(reader.fieldnames, COMPOSITE_ROLES_COLUMNS, path)
        for row in reader:
            composite_children[row["composite_role_id"]].add(row["single_role_id"])
    return composite_children


def expand_role_to_single_roles(role_id, composite_children, seen=None):
    """Resolve a role_id down to the single role(s) that actually hold
    T-code authorizations. If role_id isn't a known composite, it's
    assumed to already be a single role. Cycle-guarded against a
    misconfigured composite bundling itself back in.
    """
    if seen is None:
        seen = set()
    if role_id in seen:
        return set()
    seen.add(role_id)

    children = composite_children.get(role_id)
    if not children:
        return {role_id}

    leaves = set()
    for child in children:
        leaves |= expand_role_to_single_roles(child, composite_children, seen)
    return leaves


def build_user_tcode_roles(role_tcodes_path, user_roles_path, composite_roles_path=None):
    """Flatten role_tcodes + user_roles (+ optional composite_roles) into
    {user_id: {tcode: {single_role_id, ...}}} -- which single role(s)
    granted each T-code a user holds.
    """
    role_tcodes = load_role_tcodes(role_tcodes_path)
    composite_children = load_composite_roles(composite_roles_path) if composite_roles_path else {}

    user_tcode_roles = defaultdict(lambda: defaultdict(set))
    with open(user_roles_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        _require_columns(reader.fieldnames, USER_ROLES_COLUMNS, user_roles_path)
        for row in reader:
            user_id = row["user_id"]
            user_tcode_roles[user_id]  # noqa: B018 -- ensure the key exists even if no tcode resolves below
            for single_role_id in expand_role_to_single_roles(row["role_id"], composite_children):
                for tcode in role_tcodes.get(single_role_id, set()):
                    user_tcode_roles[user_id][tcode].add(single_role_id)
    return user_tcode_roles


def build_user_tcodes(role_tcodes_path, user_roles_path, composite_roles_path=None):
    """Flatten into {user_id: {tcode, ...}}, the flat shape detect.py needs."""
    user_tcode_roles = build_user_tcode_roles(role_tcodes_path, user_roles_path, composite_roles_path)
    return {user_id: set(tcode_roles.keys()) for user_id, tcode_roles in user_tcode_roles.items()}
