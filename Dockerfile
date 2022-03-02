FROM node:lts AS client_builder

WORKDIR /srv

RUN apt update \
    && apt upgrade -y \
    && apt clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN groupadd -r builder \
    && useradd --no-log-init -r -m -g builder builder \
    && chown builder:builder /srv

COPY --chown=builder:builder \
    ./client/package.json ./client/package-lock.json \
    ./

USER builder

RUN npm install

COPY ./client/ ./

RUN npm run build

# ------------------------------------------------------------------------------------------------ #

FROM python:3.10-slim AS ltiapp

WORKDIR /srv

# install dependencies
RUN pip install --no-cache-dir -U pip setuptools wheel

RUN apt update \
    && apt upgrade -y \
    && apt install -y --no-install-recommends gosu \
        gcc libc-dev libmariadb3 libmariadb-dev libpq5 libpq-dev \
    && apt autoremove -y && apt autoclean && apt clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./backends.requirements.txt .
RUN pip install --no-cache-dir -r backends.requirements.txt

# make an unpriviledged user and allow the user to access the data folder
RUN groupadd -r ltiapp \
    && useradd --no-log-init -r -m -g ltiapp ltiapp \
    && mkdir data && chown -R ltiapp:ltiapp data

# Dependencies have been installed. Only build the 2nd stage if necessary
COPY --chown=ltiapp:ltiapp . .

COPY --from=client_builder --chown=ltiapp:ltiapp \
    /srv/dist/ /srv/client/dist/

ENV DJANGO_SETTINGS_MODULE=draw.test_settings

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["draw.asgi", "--bind=0.0.0.0:8000"]

EXPOSE 8000
