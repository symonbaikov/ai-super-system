import json, sys, pathlib
base = pathlib.Path(__file__).resolve().parents[1]/"configs"
for fn in ["ui_config.json","parser_rules.json"]:
    p = base/fn
    j = json.loads(p.read_text(encoding="utf-8"))
    print("OK:", fn, "keys:", list(j.keys())[:5])
