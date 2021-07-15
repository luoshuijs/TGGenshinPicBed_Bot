FROM python:3.8-alpine AS base

FROM base AS runtime_1
RUN apk add --no-cache g++                                \
    && python3 -m                                         \
       pip install --user ujson~=4.0.2                    \
                          colorlog==5.0.1                 \
                          mysql-connector-python==8.0.25  \
                          python-telegram-bot==13.6       \
                          redis==3.5.3                    \
                          requests~=2.20.0                \
                          httpx~=0.18.1                   \
                          aiomysql~=0.0.21                \
    && apk del g++

FROM runtime_1 AS runtime_2
RUN apk add --no-cache libstdc++


FROM base AS dependency
ADD https://raw.githubusercontent.com/eficode/wait-for/master/wait-for /wait-for
RUN chmod a+x /wait-for


FROM runtime_2
COPY . /root/app/
COPY --from=dependency /wait-for /wait-for
WORKDIR /root/app/
ENTRYPOINT echo "Waiting for database (sleep=15)..." && sleep 15 && echo "Waiting for API..."\
    && /wait-for ${MYSQL_HOST}:${MYSQL_PORT} ${REDIS_HOST}:${REDIS_PORT} -- \
    python3 -m unittest discover tests.integration
