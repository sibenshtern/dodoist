FROM postgres:16-alpine

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && mkdir -p /docker-entrypoint-initdb.d

ENTRYPOINT ["/entrypoint.sh"]
