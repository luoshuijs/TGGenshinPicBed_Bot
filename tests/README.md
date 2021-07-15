# Tests


## Unit test

Unit tests target the core logic and test each unit of behavior in isolation.

To execute test cases, run the following command under the top level directory of the project:

```
$ python3 -m unittest discover tests.unit
```

## Integration test

**Requires docker and docker-compose.**

Docker-compose will spin up several shared dependencies the project and the test relies on:

1. MySQL / Mariadb
2. Redis

The dependencies are short-lived. Upon completion (or failure) of the test, database instances 
are destroyed.

To execute test cases, run the following command under the top level directory of the project:

```
# Copy configuration for docker-compose
$ cp tests/integration/.env.example tests/integration/.env

# Cleanup old settings
$ docker-compose -f tests/integration/docker-compose.yaml rm -fv

# Build test containers
$ docker-compose -f tests/integration/docker-compose.yaml up --abort-on-container-exit --build
```
