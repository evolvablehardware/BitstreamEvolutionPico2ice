FROM ubuntu:noble-20251013
WORKDIR /usr/local/lib

RUN apt update && apt install -y build-essential clang bison flex libreadline-dev gawk tcl-dev libffi-dev libftdi-dev mercurial graphviz xdot \
pkg-config python3 python3-pip libboost-all-dev cmake make yosys arachne-pnr python3 python3-venv python3-pip git make && rm -rf /var/cache/apt/archives /var/lib/apt/lists/*

RUN git clone https://github.com/heiljj/iCEFARM.git

WORKDIR /usr/local/app
COPY ./ /usr/local/app/

RUN python3 -m venv .venv
RUN .venv/bin/pip install pyserial numpy matplotlib sortedcontainers pytest
# client pip install broken last I checked
RUN .venv/bin/pip install -e /usr/local/lib/iCEFARM
RUN make init
RUN cp 1khz_ice27_generated.asc data/seed-hardware.asc