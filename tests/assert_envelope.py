#!/usr/bin/env python3
"""tests/assert_envelope.py — validate a function envelope on stdin against
api/v1/schema/envelope.json (JSON Schema draft 2020-12).

Usage: curl -sf $BASE/api/health | python3 tests/assert_envelope.py --schema api/v1/schema/envelope.json
Exit 0 on valid, 1 with the violations printed on failure.
"""
import argparse
import json
import sys

from jsonschema import Draft202012Validator


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schema", required=True)
    args = ap.parse_args()

    schema = json.load(open(args.schema))
    Draft202012Validator.check_schema(schema)
    doc = json.load(sys.stdin)
    errors = list(Draft202012Validator(schema).iter_errors(doc))
    if errors:
        for e in errors[:10]:
            print("SCHEMA VIOLATION: %s (path: %s)" % (e.message, "/".join(map(str, e.path))))
        if len(errors) > 10:
            print("... and %d more" % (len(errors) - 10))
        return 1
    print("envelope valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
