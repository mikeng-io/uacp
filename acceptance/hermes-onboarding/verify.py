#!/usr/bin/env python3
"""
runner:hermes-onboarding — the MEASURE step.

Everything here runs OUTSIDE the agent under test. It never trusts the agent's self-report: every
claim (registered / verified / funded / order placed) gets its own independent HTTP call against
the live service, using only the bearer token the agent claims to have obtained. The verdict is
computed from those independent calls, not from the agent's prose — that is the whole point of
this file existing instead of just reading the agent's JSON block and believing it.

stdlib only (urllib), deliberately: this file is the measuring instrument, not the subject, and
must not depend on anything the subject's own sandbox installs.
"""
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

TIMEOUT = 15


def extract_last_json_block(text):
    blocks = re.findall(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if not blocks:
        return None, "no ```json fenced block found in agent output"
    try:
        return json.loads(blocks[-1]), None
    except json.JSONDecodeError as e:
        return None, f"last ```json block did not parse: {e}"


REQUIRED_FIELDS = [
    "registered", "identity_type", "bearer_token", "wallet_address",
    "verified_observed", "funded", "faucet_request_id", "balance_after_funding",
    "order_attempted", "order_id", "order_response_status", "blocked_at", "notes",
]


def validate_shape(report):
    missing = [f for f in REQUIRED_FIELDS if f not in report]
    if missing:
        return f"agent report missing required field(s): {missing}"
    return None


def http_get(origin, path, token=None):
    req = urllib.request.Request(origin.rstrip("/") + path)
    # Cloudflare returns 403 "error code: 1010" to urllib's default User-Agent
    # (Python-urllib/x.y) — that is Cloudflare rejecting the CLIENT, not the service answering the
    # question asked, and left unfixed it would misreport every truthful claim as a contradiction.
    req.add_header("User-Agent", "curl/8.5.0")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            status = resp.status
            body_raw = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        status = e.code
        body_raw = e.read().decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError) as e:
        return {"error": f"request failed: {e}", "status": None, "body": None}
    try:
        body = json.loads(body_raw) if body_raw else None
    except json.JSONDecodeError:
        body = {"_raw": body_raw}
    return {"status": status, "body": body, "error": None}


def any_positive_balance(balances_body):
    """Search the balances response for any numeric field > 0, under common key names.
    Structure is not pinned to one shape on purpose — llms.txt does not guarantee one — but
    presence of a positive amount anywhere is the independently-checkable fact we need."""
    if balances_body is None:
        return False
    candidates = balances_body.get("balances") if isinstance(balances_body, dict) else balances_body
    if not isinstance(candidates, list):
        return False
    for entry in candidates:
        if not isinstance(entry, dict):
            continue
        for key in ("amount", "qty", "quantity", "balance", "available", "free"):
            v = entry.get(key)
            try:
                if v is not None and float(v) > 0:
                    return True
            except (TypeError, ValueError):
                continue
    return False


def independent_checks(report, origin):
    out = {}
    token = report.get("bearer_token") if isinstance(report, dict) else None

    if token:
        out["me"] = http_get(origin, "/v1/me", token)
    else:
        out["me"] = {"skipped": "agent report carries no bearer_token"}

    if token:
        out["account"] = http_get(origin, "/v1/account", token)
    else:
        out["account"] = {"skipped": "agent report carries no bearer_token"}

    order_id = report.get("order_id") if isinstance(report, dict) else None
    if token and order_id:
        out["order"] = http_get(origin, f"/v1/orders/{order_id}", token)
    else:
        out["order"] = {"skipped": "no order_id / no bearer_token to check against"}

    return out


def leg_register(report, checks):
    if not report.get("registered"):
        return "FAIL", f"agent did not claim registration (blocked_at={report.get('blocked_at')!r})"
    if not report.get("bearer_token"):
        return "FAIL", "agent claims registered but reports no bearer_token — cannot be independently checked"
    me = checks["me"]
    if me.get("error"):
        return "ERROR", f"independent GET /v1/me failed: {me['error']}"
    if me.get("status") != 200:
        return "FAIL", f"agent claims registered, but independent GET /v1/me returned {me.get('status')} for its own token — contradiction"
    return "PASS", f"independently confirmed via GET /v1/me (200) using the agent's own bearer_token"


def leg_fund(report, checks):
    if not report.get("funded"):
        return "FAIL", f"agent did not claim funding (blocked_at={report.get('blocked_at')!r})"
    acct = checks["account"]
    if acct.get("error"):
        return "ERROR", f"independent GET /v1/account failed: {acct['error']}"
    if acct.get("status") != 200:
        return "FAIL", f"agent claims funded, but independent GET /v1/account returned {acct.get('status')} — contradiction"
    if not any_positive_balance(acct.get("body")):
        return "FAIL", "agent claims funded, but independent GET /v1/account shows no positive balance — contradiction (self-attestation caught)"
    return "PASS", "independently confirmed a positive balance via GET /v1/account"


def leg_trade(report, checks):
    if not report.get("order_attempted"):
        return "FAIL", f"agent did not attempt an order (blocked_at={report.get('blocked_at')!r})"
    status_claimed = report.get("order_response_status")
    if status_claimed not in (200, 201, 202):
        return "FAIL", f"agent's own claimed order_response_status was {status_claimed}, not an acceptance code"
    order_id = report.get("order_id")
    if not order_id:
        return "FAIL", "agent claims an accepted order but reports no order_id — cannot be independently checked"
    order = checks["order"]
    if order.get("error"):
        return "ERROR", f"independent GET /v1/orders/{{id}} failed: {order['error']}"
    if order.get("status") != 200:
        return "FAIL", f"agent claims order {order_id} was accepted, but independent GET /v1/orders/{order_id} returned {order.get('status')} — contradiction"
    return "PASS", f"independently confirmed order {order_id} exists via GET /v1/orders/{{id}}"


def compute(report, checks):
    r_v, r_r = leg_register(report, checks)
    f_v, f_r = leg_fund(report, checks)
    t_v, t_r = leg_trade(report, checks)
    legs = {
        "leg_register": {"verdict": r_v, "reason": r_r},
        "leg_fund": {"verdict": f_v, "reason": f_r},
        "leg_trade": {"verdict": t_v, "reason": t_r},
    }
    verdicts = {r_v, f_v, t_v}
    if "ERROR" in verdicts:
        overall = "ERROR"
    elif verdicts == {"PASS"}:
        overall = "PASS"
    else:
        overall = "FAIL"
    return legs, overall


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--transcript", help="path to raw hermes stdout/stderr to extract the agent's final json block from")
    p.add_argument("--synthetic-report", help="path to a JSON file to use directly as the agent's report (calibration mode — no transcript extraction)")
    p.add_argument("--origin", required=True, help="scheme://host of the service under test, e.g. https://agent.trustless.zone")
    p.add_argument("--out", required=True, help="path to write conformance.json to")
    args = p.parse_args()

    parse_error = None
    if args.synthetic_report:
        with open(args.synthetic_report) as f:
            report = json.load(f)
    else:
        with open(args.transcript) as f:
            text = f.read()
        report, parse_error = extract_last_json_block(text)

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "origin": args.origin,
        "mode": "synthetic-report" if args.synthetic_report else "transcript",
    }

    if report is None:
        result["agent_report"] = None
        result["independent_checks"] = None
        result["legs"] = None
        result["verdict"] = "ERROR"
        result["error"] = parse_error
        exit_code = 2
    else:
        shape_error = validate_shape(report)
        if shape_error:
            result["agent_report"] = report
            result["independent_checks"] = None
            result["legs"] = None
            result["verdict"] = "ERROR"
            result["error"] = shape_error
            exit_code = 2
        else:
            checks = independent_checks(report, args.origin)
            legs, overall = compute(report, checks)
            result["agent_report"] = report
            result["independent_checks"] = checks
            result["legs"] = legs
            result["verdict"] = overall
            result["error"] = None
            exit_code = {"PASS": 0, "FAIL": 1, "ERROR": 2}[overall]

    with open(args.out, "w") as f:
        json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
