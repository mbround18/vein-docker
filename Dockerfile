# --------------- #
# -- Steam CMD -- #
# --------------- #
FROM steamcmd/steamcmd:ubuntu

ENV TZ=America/Los_Angeles \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install dependencies in a single layer and clean up
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
        # Essential tools
        ca-certificates \
        tzdata \
        # Runtime dependencies for Unreal Engine game server
        lib32gcc-s1 \
        libatomic1 \
        libasound2t64 \
        libpulse0 \
        libgl1 \
        # Management utilities
        curl wget \
        sudo gosu \
        crudini jq \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* \
    && gosu nobody true

# Install uv for Python script execution (multi-platform)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Container metadata
ARG GITHUB_SHA="not-set"
ARG GITHUB_REF="not-set"
ARG GITHUB_REPOSITORY="not-set"

# Setup steam user and permissions in a single layer
RUN if getent passwd 1000 > /dev/null; then userdel $(getent passwd 1000 | cut -d: -f1); fi \
    && if getent group 1000 > /dev/null; then groupdel $(getent group 1000 | cut -d: -f1); fi \
    && groupadd -g 1000 steam \
    && useradd -u 1000 -g 1000 -d /home/steam -s /bin/bash -m steam \
    && echo "steam ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers \
    && mkdir -p /tmp/dumps \
    && chmod ugo+rw /tmp/dumps

USER steam
WORKDIR /home/steam

# Runtime environment variables
ENV HOME=/home/steam \
    USER=steam \
    DISPLAY=:1 \
    APP_ID=2131400 \
    INSTALL_DIR=/home/steam/vein
ENV LD_LIBRARY_PATH="/home/steam/.steam/sdk32:/home/steam/.steam/sdk64:${LD_LIBRARY_PATH:-}"

# Copy scripts with correct permissions
COPY --chown=steam:steam --chmod=755 ./scripts/entrypoint.sh /entrypoint.sh
COPY --chown=steam:steam --chmod=755 ./scripts/configure_server.py /usr/local/bin/configure_server.py

# Create base directories (Steam SDK links created at runtime by entrypoint)
RUN mkdir -p /home/steam/.steam /home/steam/vein

WORKDIR /home/steam/vein

# Server ports
EXPOSE 7777/udp 27015/udp 27016/udp

ENTRYPOINT ["/entrypoint.sh"]
