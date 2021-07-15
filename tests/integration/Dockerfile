FROM python:3.8-alpine AS runtime
WORKDIR /root/app/
ADD https://raw.githubusercontent.com/eficode/wait-for/master/wait-for /wait-for
RUN chmod a+x /wait-for
RUN apk add --no-cache build-base                  \
    && python3 -m                                  \
       pip install colorlog==5.0.1                 \
                   mysql-connector-python==8.0.25  \
                   python-telegram-bot==13.6       \
                   redis==3.5.3                    \
                   requests~=2.20.0                \
                   httpx~=0.18.1                   \
                   ujson~=4.0.2                    \
                   aiomysql~=0.0.21


FROM runtime
COPY . /root/app/
COPY --from=runtime /wait-for /wait-for
WORKDIR /root/app/
ENTRYPOINT echo "Waiting for database (sleep=30s)..." && sleep 30 \
    && /wait-for ${MYSQL_HOST}:${MYSQL_PORT} ${REDIS_HOST}:${REDIS_PORT} -- \
    python3 -m unittest discover tests.integration
