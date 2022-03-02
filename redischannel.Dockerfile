FROM gitlab-container.tba-hosting.de/lpa-aflek-alice/excalidraw-lti-application:latest
RUN apt update && apt install -y --no-install-recommends gcc libc-dev \
    && pip install --no-cache-dir channels-redis \
    && apt remove -y gcc libc-dev && apt autoremove -y && apt autoclean \
    && apt clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
