# Headless Godot 4 for running gdUnit4 tests and exports on the CPU-only server.
# Build: docker build -t godot-headless server/godot-headless
# Run:   docker run --rm -v $PWD/game:/game godot-headless --headless --path /game -s res://addons/gdUnit4/bin/GdUnitCmdTool.gd --add res://tests --ignoreHeadlessMode
ARG GODOT_VERSION=4.3
FROM debian:bookworm-slim
ARG GODOT_VERSION
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates unzip wget libfontconfig1 && rm -rf /var/lib/apt/lists/*
RUN wget -q https://github.com/godotengine/godot/releases/download/${GODOT_VERSION}-stable/Godot_v${GODOT_VERSION}-stable_linux.x86_64.zip -O /tmp/godot.zip \
 && unzip -q /tmp/godot.zip -d /opt && mv /opt/Godot_v${GODOT_VERSION}-stable_linux.x86_64 /usr/local/bin/godot && rm /tmp/godot.zip && chmod +x /usr/local/bin/godot
WORKDIR /game
ENTRYPOINT ["godot"]
