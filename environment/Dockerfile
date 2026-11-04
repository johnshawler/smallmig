# Offline local isolation-test image. Not a published Codex environment.
FROM debian:13-slim@sha256:f6b08b09a05725f9431502d3b5714f5c4576e82c1a84fa1debe0c24a7e0c3ec4
COPY rootfs/ /
WORKDIR /app/SmallMig
COPY source/ ./
RUN python3 environment/startup_check.py
CMD ["python3", "environment/startup_check.py", "--emulators"]
