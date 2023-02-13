FROM node:lts AS client_builder

WORKDIR /srv

RUN apt update \
    && apt upgrade -y \
    && apt clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* \
    && npm i -g -f pnpm

RUN groupadd -r builder \
    && useradd --no-log-init -r -m -g builder builder \
    && chown builder:builder /srv

COPY --chown=builder:builder \
    ./client/package.json ./client/pnpm-lock.yaml \
    ./

USER builder

RUN pnpm install --frozen-lockfile

COPY ./client/ ./

RUN pnpm run build

# ------------------------------------------------------------------------------------------------ #

FROM python:3.10-slim AS wheel_builder

WORKDIR /opt

RUN apt update \
    && apt upgrade -y \
    && apt install -y --no-install-recommends \
    gcc libc-dev libmariadb-dev libpq-dev \
    && apt autoremove -y && apt autoclean && apt clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN groupadd -r builder \
    && useradd --no-log-init -r -m -g builder builder \
    && chown builder:builder /opt

USER builder

COPY --chown=builder:builder ./wheels.requirements.txt .

RUN mkdir -p wheels
RUN pip install --no-cache-dir -U pip setuptools wheel
RUN pip wheel -r wheels.requirements.txt -w ./wheels/

# ------------------------------------------------------------------------------------------------ #

FROM python:3.10-slim AS ltiapp

WORKDIR /srv

# install dependencies
RUN pip install --no-cache-dir -U pip setuptools wheel

RUN apt update \
    && apt upgrade -y \
    && apt install -y --no-install-recommends gosu libmariadb3 libpq5 \
    && apt autoremove -y && apt autoclean && apt clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --from=wheel_builder /opt/wheels /opt/wheels

COPY ./backends.requirements.txt .
RUN pip install --no-cache-dir -r backends.requirements.txt --find-links /opt/wheels

# make an unpriviledged user and allow the user to access the data folder
RUN groupadd -r ltiapp \
    && useradd --no-log-init -r -m -g ltiapp ltiapp \
    && mkdir data && chown -R ltiapp:ltiapp data

# Dependencies have been installed. Only build the 2nd stage if necessary
COPY --from=client_builder --chown=ltiapp:ltiapp \
    /srv/dist/ /srv/client/dist/

COPY --chown=ltiapp:ltiapp . .

ENV DJANGO_SETTINGS_MODULE=draw.test_settings

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["draw.asgi", "--bind=0.0.0.0:8000"]

EXPOSE 8000

LABEL org.opencontainers.image.source https://github.com/Hyperchalk/Hyperchalk
