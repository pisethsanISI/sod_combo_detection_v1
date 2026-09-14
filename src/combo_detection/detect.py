"""Core combination-rule detection: matching a user's T-code access against
ALL functions of an N-function combination rule (generalizes the
pairwise "both sides must match" check to "every function must match").
"""


def detect_combination_conflicts(rules, user_tcodes, user_tcode_roles=None):
    """Return one finding per (user, rule) pair where the user's T-code
    access covers at least one T-code from EVERY function in the rule.

    A rule with any function that has zero T-codes at all (a physical or
    organizational-only step, see ruleset.rules_needing_manual_tracking)
    can never produce a finding here -- that's deliberate, not a bug, since
    an empty set never intersects anything. Those rules must be tracked as
    manual/organizational controls instead.

    user_tcode_roles is the optional {user_id: {tcode: {role_id, ...}}}
    provenance from access.build_user_tcode_roles(). When given, each
    finding also names which role(s) granted each matched function's
    T-code(s), so the report says which role to fix, not just which user
    is affected.
    """
    findings = []
    for user_id, tcodes in user_tcodes.items():
        for rule in rules:
            matches = [tcodes & fn["tcodes"] for fn in rule["functions"]]
            if all(matches):
                findings.append(
                    {
                        "user_id": user_id,
                        "combo_id": rule["combo_id"],
                        "process_area": rule["process_area"],
                        "category": rule["category"],
                        "risk_level": rule["risk_level"],
                        "control_type": rule.get("control_type", ""),
                        "functions": [
                            {
                                "name": fn["name"],
                                "matched_tcodes": sorted(match),
                                "granting_roles": sorted(_roles_for(user_tcode_roles, user_id, match)),
                            }
                            for fn, match in zip(rule["functions"], matches)
                        ],
                        "business_impact": rule["business_impact"],
                        "suggested_mitigation": rule["suggested_mitigation"],
                        "status": rule.get("status", ""),
                        "notes": rule.get("notes", ""),
                    }
                )
    return findings


def _roles_for(user_tcode_roles, user_id, tcodes):
    if not user_tcode_roles:
        return set()
    roles = set()
    for tcode in tcodes:
        roles |= user_tcode_roles.get(user_id, {}).get(tcode, set())
    return roles
