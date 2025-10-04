import json, os, sys
root=os.path.dirname(os.path.dirname(__file__))
paths=['configs/profiles_config.json','configs/risk_policy.json','configs/trading_config.json','configs/whales_config.json','configs/llm_router.json','configs/search_templates.json']
ok=True
for p in paths:
  try:
    json.load(open(os.path.join(root,p),'r',encoding='utf-8'))
    print('[OK]',p)
  except Exception as e:
    ok=False
    print('[ERR]',p, e)
sys.exit(0 if ok else 1)
