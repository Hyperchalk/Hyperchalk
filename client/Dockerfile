FROM node:lts

WORKDIR /srv

RUN apt update \
    && apt upgrade -y \
    && apt clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* \
    && npm i -g pnpm

RUN groupadd -r builder \
    && useradd --no-log-init -r -m -g builder builder \
    && chown builder:builder /srv

COPY --chown=builder:builder \
    ./package.json ./pnpm-lock.yaml \
    ./

USER builder

RUN pnpm install --frozen-lockfile

COPY ./ ./

ENTRYPOINT [ "pnpm", "run" ]
CMD [ "build" ]
