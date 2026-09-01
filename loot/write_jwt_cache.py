import json
jwt = json.load(open('/home/ubuntu/pwand-playwright/xunlei_jwt.json'))
json.dump({'jwt': jwt.get('token',''), 'ts': jwt.get('ts')},
          open('/home/ubuntu/pwand-playwright/xunlei_jwt_cache.json','w'))
print('jwt cache written, len:', len(jwt.get('token','')))
