import json
tok = json.load(open('/home/ubuntu/pwand-playwright/xunlei_token.json'))
jwt = json.load(open('/home/ubuntu/pwand-playwright/xunlei_jwt.json'))
tok['jwt'] = jwt.get('token','')
tok['jwt_ts'] = jwt.get('ts')
json.dump(tok, open('/home/ubuntu/pwand-playwright/xunlei_token.json','w'))
print('merged keys:', list(tok.keys()), 'jwt len:', len(tok.get('jwt','')))
