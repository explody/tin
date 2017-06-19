Not even close to done, but nearing usefulness.

Barebones example.  For the APIs that are scaffolded as YML under apis/, you'll need to create a yaml file for the credentials for this to work.

See 'okta.yml' and 'ipam.yml' in the apis directory.

```python
#!/usr/bin/env python3

import pprint
import logging
import simplejson as json
from apeye.api import ApeyeApi

# -*- coding: utf-8 -*-
__author__ = 'mculbertson'

logging.getLogger("requests").setLevel(logging.WARNING)

print("##### Fetching an example section from IPAM")
ipam = ApeyeApi(conffile='apis/phpipam/ipam.yml')

token_req = ipam.user.get_token()
token = token_req['data']['token']

ipam.conf.set('authtype', 'header')
ipam.conf.set('credentials', {'phpipam-token': token})

sec = ipam.sections.get(id=3)

pprint.pprint(sec)

print("##### Now fire up okta and grab a user object")
okta = ApeyeApi(conffile='apis/okta/okta.yml')
#
pprint.pprint(okta.user.get(uid='mculbertson@pivotal.io')['profile'])
```

Sample edit
