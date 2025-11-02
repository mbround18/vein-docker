# --------------- #
# -- Steam CMD -- #
# --------------- #
FROM steamcmd/steamcmd:ubuntu

ENV TZ=America/Los_Angeles \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive
    
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y -qq \
        build-essential \
        htop net-tools nano gcc g++ gdb \
        curl wget zip unzip \
        cron sudo gosu dos2unix jq crudini \
        tzdata \
        ca-certificates \
        lib32gcc-s1 \
        wine64 winbind xvfb \
    && rm -rf /var/lib/apt/lists/* \
    && gosu nobody true \
    && dos2unix

# Remove any existing user or group with ID 1000 and create steam user
RUN if getent passwd 1000 > /dev/null; then userdel $(getent passwd 1000 | cut -d: -f1); fi \
    && if getent group 1000 > /dev/null; then groupdel $(getent group 1000 | cut -d: -f1); fi \
    && groupadd -g 1000 steam \
    && useradd -u 1000 -g 1000 \
      -d /home/steam \
      -s /bin/bash \
      -m steam \
    && chmod ugo+rw /tmp/dumps

# Container information
ARG GITHUB_SHA="not-set"
ARG GITHUB_REF="not-set"
ARG GITHUB_REPOSITORY="not-set"

RUN echo "steam ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

USER steam

WORKDIR /home/steam

ENV HOME=/home/steam \
    USER=steam \
    LD_LIBRARY_PATH="/home/steam/.steam/sdk32:/home/steam/.steam/sdk64:${LD_LIBRARY_PATH}" \
    DISPLAY=:1 \
    APP_ID=2131400 \
    INSTALL_DIR=/home/steam/vein

# Add entrypoint
COPY --chown=steam:steam ./scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh \
    && mkdir -p $HOME/.steam \
    && mkdir -p $INSTALL_DIR \
    && ln -s $HOME/.local/share/Steam/steamcmd/linux32 $HOME/.steam/sdk32 \
    && ln -s $HOME/.local/share/Steam/steamcmd/linux64 $HOME/.steam/sdk64 \
    && ln -s $HOME/.steam/sdk32/steamclient.so $HOME/.steam/sdk32/steamservice.so || true \
    && ln -s $HOME/.steam/sdk64/steamclient.so $HOME/.steam/sdk64/steamservice.so || true

WORKDIR /home/steam/vein

# Ports are game-specific; define via docker-compose as needed

EXPOSE 27015/udp
EXPOSE 27016/udp
EXPOSE 7777/udp

ENTRYPOINT ["/entrypoint.sh"]
