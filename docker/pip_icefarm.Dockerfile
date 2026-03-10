# This image runs the icefarm client off a pip installation
FROM ubuntu:noble-20251013 AS venv-builder
RUN apt update && apt install -y python3 python3-pip python3-venv python3-pip && rm -rf /var/cache/apt/archives /var/lib/apt/lists/*

WORKDIR /usr/local/app
RUN python3 -m venv .venv
RUN .venv/bin/pip install pyserial numpy matplotlib sortedcontainers pytest ascutil icefarm

FROM ubuntu:noble-20251013
WORKDIR /usr/local/lib

RUN apt update && apt install -y build-essential clang bison flex libreadline-dev gawk tcl-dev libffi-dev libftdi-dev mercurial graphviz xdot \
pkg-config python3 python3-pip libboost-all-dev cmake make yosys arachne-pnr python3-venv git make && rm -rf /var/cache/apt/archives /var/lib/apt/lists/*

COPY ./ /usr/local/app/
WORKDIR /usr/local/app

COPY --from=venv-builder /usr/local/app/.venv /usr/local/app/.venv

RUN make init
