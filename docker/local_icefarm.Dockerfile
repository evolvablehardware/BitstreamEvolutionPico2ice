# This image runs the icefarm client off a local installation, needs icefarm repo to be cloned in /usr/local/lib
FROM noble-20251013 AS venv-builder
RUN apt update && apt install -y python3 python3-pip python3-venv python3-pip && rm -rf /var/cache/apt/archives /var/lib/apt/lists/*

WORKDIR /usr/local/app
RUN python3 -m venv .venv
RUN .venv/bin

FROM ubuntu:noble-20251013
WORKDIR /usr/local/lib

RUN apt update && apt install -y build-essential clang bison flex libreadline-dev gawk tcl-dev libffi-dev libftdi-dev mercurial graphviz xdot \
pkg-config python3 python3-pip libboost-all-dev cmake make yosys arachne-pnr python3 python3-venv python3-pip git make && rm -rf /var/cache/apt/archives /var/lib/apt/lists/*

COPY iCEFARM/ /usr/local/lib/iCEFARM/

WORKDIR /usr/local/app
COPY ./ /usr/local/app/

COPY --from=venv-builder /usr/local/app/.venv /usr/local/app/.venv
RUN .venv/bin/pip install /usr/local/lib/iCEFARM/

RUN make init
