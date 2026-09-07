FROM postgis/postgis:13-3.5
#  instruct local Dockerfile to directly COPY the maintenance scripts straight from the production folder
COPY ./compose/production/postgres/maintenance /usr/local/bin/maintenance
RUN chmod +x /usr/local/bin/maintenance/*
RUN mv /usr/local/bin/maintenance/* /usr/local/bin \
    && rmdir /usr/local/bin/maintenance

COPY ./compose/local/postgres/init_template1.sh /docker-entrypoint-initdb.d/init_template1.sh
RUN chmod +x /docker-entrypoint-initdb.d/init_template1.sh
