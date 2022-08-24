FROM node:lts

WORKDIR /srv

RUN apt update \
    && apt upgrade -y \
    && apt clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN groupadd -r builder \
    && useradd --no-log-init -r -m -g builder builder \
    && chown builder:builder /srv

COPY --chown=builder:builder \
    ./package.json ./package-lock.json \
    ./

USER builder

RUN npm install --production

COPY ./ ./

ENTRYPOINT [ "npm", "run" ]
CMD [ "build" ]
