HEAD: [![pipeline status](https://gitlab.com/explody/tin/badges/main/pipeline.svg)](https://gitlab.com/explody/tin/-/commits/main) [![coverage report](https://gitlab.com/explody/tin/badges/main/coverage.svg)](https://gitlab.com/explody/tin/-/commits/main)
Release: [![pipeline status](https://gitlab.com/explody/tin/badges/release/pipeline.svg)](https://gitlab.com/explody/tin/-/commits/release) [![coverage report](https://gitlab.com/explody/tin/badges/release/coverage.svg)](https://gitlab.com/explody/tin/-/commits/release)

# Tin

Tin is a thin and minimal wrapper around [python requests](https://docs.python-requests.org/en/master/index.html) intended as a generic REST API client library.  [APIs are defined](https://gitlab.com/explody/tin-apis/) as [YAML](https://yaml.org/) wherein API services, enpoints, methods and such that API specs can be updated easily without changing python code.  A bit like a poor man's [Swagger/OpenAPI](https://www.openapis.org/).


> **On the subject of Swagger/OpenAPI**
>
> If the REST API you need to interact with publishes an OpenAPI spec, you very
> likely do not need Tin.  There are a variety of much more robust
> [OpenAPI tools](https://openapi.tools/) that will generate API
> client code, among other functions.
> Tin was made with services that _don't_ publish OpenAPI data in mind. That being said, it'll still work fine with any REST API that speaks JSON.

## Features

* Supports multiple environment definitions per API
* Basic, header and parameter based authentication
* Credentials from a YML or JSON file, or environment vars
* A minimal model system where lists of json dicts returned from a service
  can be instantiated as custom objects with canned CRUD methods such
  as `.create()` and `.save()`
* Simple field validation for models, for specifying required and/or read-only fields.
* Requests session support
* Generally any option that can be passed to requests.

## Usage

With an service, API and model files such as

**Service definition**

```yaml
---
environments:
  production:
    host: yourhost.service.com
    scheme: https
    port: 443
    credentials: ~/path/to/credentials.yml
    auth_type: basic
    ssl:
      verify: true
    api_file: path/to/service-api.yml
    model_file: path/to/service-models.yml
common:
  # Common settings apply to all environments
  content_type: "application/json"
  basepath: "/api/v2"
  params:
    may: ["links", "filter_by", "filter_value"]
```

**API Definition**

```yaml
---
things:
  list_data_key: "things"  # if json data comes back under a toplevel key
  model: thing  # Optional: associated model from the models file
  methods:
    create:
      method: POST
      path: /things
      object_method: create  # this method will be associated with model_instance.create()
      expect: 201
    get:
      method: GET
      path: /things/:id
      object_method: read  # this method will be associated with model_instance.refresh()
    list:
      method: GET
      path: /things
```

**Models Definition**

```yaml
---
thing:
  id_attr: id
  read_only:  # read-only
    - id
  must:  # When saving a newly created model instance, these attrs are required
    - name
    - email
  may:  # Optional attrs that will be sent to the service API if set in the model instance
    - description
    - extra_stuff

```

**Tin can be used like this**

```python
from tin.api import TinApi
myapi = TinApi(config_file='path/to/myapi_definition.yml', environment='production')

things = myapi.things.list() # returns {'things': [<myapi.things.thing>, <myapi.things.thing>...]}

things = myapi.things.list(nomodel=True) # returns {'things': [ {'id': 1, name: 'thingname', 'email': 'mail@example.com'} ... ]

thing = myapi.things.get(1)
thing = myapi.things.get(id=1)

thing.name   # "thingname"
thing.name = "newname"
thing.save()
thing.name   # "newname"

newthing = myapi.things.model({})
newthing.save()   # fails validation as name and email aren't set

newthing.name = 'new thing'
newthing.email = 'mail@example.com'
newthing.save()   # succeeds

newthing.update({'name': 'new name'})  # updates instance and makes Update API call

newthing.delete()

```

