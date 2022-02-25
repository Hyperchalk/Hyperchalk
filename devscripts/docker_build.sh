#!/bin/bash
docker build \
    -t drawlti:latest \
    -t gitlab-container.tba-hosting.de/lpa-aflek-alice/excalidraw-lti-application:latest \
    --platform linux/x86-64 .

docker push gitlab-container.tba-hosting.de/lpa-aflek-alice/excalidraw-lti-application:latest
