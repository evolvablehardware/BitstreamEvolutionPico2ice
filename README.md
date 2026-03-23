# BitstreamEvolution
An Open Source Toolchain for the artificial evolution of FPGA bitstreams using genetic algorithms.

# Setup Overview
- Obtain [pico2ice](https://pico2-ice.tinyvision.ai/) development boards.
- Follow the [iCEFARM](https://github.com/evolvablehardware/iCEFARM?tab=readme-ov-file#icefarm-setup) setup steps included in the iCEFARM repository. The Client Usage section can be ignored. Alternately, obtain access to an existing setup.
- Follow the [BitstreamEvolution docker steps](#docker).
- Run the [live plots](#viewing-live-plots-from-a-container)

## Temporary iCEFARM Notes
Follow the setup overview.
iCEFARM needs to be running before bitstreamevolution.
If you run into issues, restart the icefarm stack in addition to the bitstreamevolution components.
iCEFARM will need to be setup and running before this.
BitstreamEvolution can be run through docker, see [setup](#docker).
The pulse count firmware listens on pin ICE_27/RPI_GPIO_20. The RANDOM initialization mode should now be working.
The pulse count fitness function is currently overridden regardless of whether you use tolerant or sensitive:
$$\frac{sum(pulses \neq 0)} {MCE(expected, actual)}$$
I've messed around with this one a bit too. It seems to work better for clocked seeds but worse for non clocked seeds:
$$\frac{ \frac {1} {MSE(expected, actual)}} {1 + \sum max(|p-mean(P)| - 0.03*expected, 0)^2}$$
The use of variance promotes circuits to rely on less undefined behavior, which seems to work while when evaluating across multiple devices. This may not be the case after the clock is disabled though.
In addition to the usual python packages, two additional are required:
- icefarm, allows use of icefarm system
- ascutil, provides significantly faster circuit mutations

See [```data/farmconfig.ini```](.data/farmconfig.ini) for an example config. This is the config used when running through Docker. Configuration values not present in this example config may produce unexpected behavior.
All of the selection methods aside from MAP work. New parameters include annotations.

### Seed file descriptions
- ```data/1kz_ice27_generated.asc``` is a 1k pulse generator synthesized from verilog with no modifications. No attempt to disable clocks has been made.
- ```data/ice27_only.asc``` contains routing from pin 27 using io tile 18,31 to logic 18 29. All other tiles are empty and all clocks are in theory unaccessible so long as column restraint notes in ```data/farmconfig.ini``` is followed.
- ```data/ice27_only_no_logic.asc``` is the same as previous but with logic tile removed. Requires col 52 (1 index) access to remake connection present in previous. Probably best just to use previous seed but this is included as a minimal working seed.

## Table of Contents
- [BitstreamEvolution](#bitstreamevolution)
  - [Table of Contents](#table-of-contents)
  - [Setup](#setup)
    - [Requirements](#requirements)
    - [Installing the dependencies](#installing-the-dependencies)
    - [Configuring the BistreamEvolution core](#configuring-the-bitstreamevolution-core)
      - [Primary Targets](#primary-targets)
      - [Targets for building Project Icestorm tools](#targets-for-building-project-icestorm-tools)
	  - [Clean targets](#clean-targets)
    - [Docker](#docker)
    - [Issues with setup](#issues-with-setup)
      - [USB permission denied](#usb-permission-denied)
  - [Usage](#usage)
    - [Configuration](#configuration)
    - [Running](#running)
    - [Troubleshooting](#troubleshooting)
  - [Contributing](#contributing)
  - [License](#license)

## Setup
Instructions for setting up the hardware is available at [the Evolvable Hardware website](https://evolvablehardware.org/setup.html).

Setting up BitstreamEvolution involves configuring the
BitstreamEvolution core, the [Project Icestorm](http://www.clifford.at/icestorm/)
tools, and the Arduino components. While BitstreamEvolution should run
on any Linux distribution and likely other Unix-based systems, the
instructions assume you are running a Debian-based distrubtion such as
Debian or Ubuntu. It's recommended that BitstreamEvolution be run through [Docker](#docker).

### Requirements
BitstreamEvolution requires Python version 3.12 or higher.

BistreamEvolution requires the following libraries and packages:
  * build-essential
  * clang
  * bison
  * flex
  * libreadline-dev
  * gawk
  * tcl-dev
  * libffi-dev
  * libftdi-dev
  * git
  * mercurial
  * graphviz
  * xdot
  * pkg-config
  * python3
  * python3-pip
  * libboost-all-dev
  * cmake
  * make

BitstreamEvolution alse requires the following Python libraries:
  * pyserial
  * matplotlib
  * numpy
  * sortedcontainers
  * icefarm
  * ascutil
  * pytest (optional, used to run tests if desired)

### Installing the dependencies
Each of the dependencies above has a corresponding `apt` package of the
same name. For other package managers the package name may be different.
For Debian-based distributions and other distributions that use `apt`,
the packages can all be installed at once with the following commands:

```bash
sudo apt update && sudo apt upgrade  # Optional, but recommended
sudo apt install build-essential clang bison flex libreadline-dev gawk tcl-dev libffi-dev libftdi-dev mercurial graphviz xdot \
pkg-config python3 python3-pip libboost-all-dev cmake make yosys arachne-pnr
```
The Python libraries can be installed in one command in any Linux
distribution as follows:

```bash
python3 -m pip install pyserial numpy matplotlib sortedcontainers pytest icefarm ascutil
```
### Configuring the BitstreamEvolution core
Although BitstreamEvolution doesn't require any building or
compilation (other than the Project Icestorm tools), it utilizes make
targets to simplify configuration. The simplest and recommended way to
configure the BitstreamEvolution core is to run `sudo make` in the root
directory of BitstreamEvolution, which will default to running the
target `all`. To allow users to optimize their configuration and save
space (BitstreamEvolution with all its tools is around 2.2 GB), other
targets are exposed. The description of each target is given in the
tables below.

#### Primary targets
These targets are responsible for the setup and configuration of
BitstreamEvolution and some of its dependencies. Note that the `all`
target performs the actions of all other targets (except for the clean
targets). One reason to utilize one of the targets other than `all` is
if the user wants to reconfigure something or if they would like to
manually install or have already installed the Project Icestorm
tools.

|Target|Actions|
|------|-------|
|`all`|Creates the directories for logging data, initializes the default configuration settings installs all the Project Icestorm tools, and creates and writes the udev rules for the PicoIce board|
|`init`|Creates the directories for logging and initializes the default configuration settings|
|`udev-rules`|Creates and writes the udev rules for the PicoIce board|

#### Targets for building Project Icestorm tools
These targets are used to individually build the tools
BitstreamEvolution depends on. In general, they are only useful if some
of the Project Icestorm tools have already been installed and the user
does not want to overwrite the previous installs or wants to save on
disk space.

|Target|Actions|
|------|-------|
|`icestorm-tools`|Builds and installs all the Project Icestorm tools|
|`icestorm`|Builds and install just the icestorm tools (e.g. icepack, iceprog)|
|`arachne-pnr`|Builds and installs just the arachne-pnr tool|
|`yosys`|Builds and installs just the yosys tools|

#### Clean targets
*In general, use of these targets is not recommended*. Since
BitstreamEvolution does not build any intermediate targets, clean
targets are used to get rid of other automatically generated files such
as the workspace defaults and the tools. In particular, cleaning the
latter is not recommended as this makes it more difficult to uninstall
the project Icestorm tools. So far, the primary use of these targets has
been for testing and maintenance of the project.

|Target|Actions|
|------|-------|
|`clean`|Removes the default permanent data logging directories and their contents as well as all the build directories for the Project Icestorm tools (*but it does not uninstall them*)|
|`clean-workspace`|Removes the default permanent data logging directories and their contents|
|`clean-tools`|Removes all the build directories for the Project Icestorm tools (*but it does not uninstall them*)|

### Setup and Start iCEFARM
Follow the setup instructions in the [iCEFARM repository](https://github.com/evolvablehardware/iCEFARM). You may skip the `Client Usage` section. If something goes wrong, you should restart the iCEFARM system in addition to BitstreamEvolution.

### Docker
Note that the live plots will not function while using a container. If it is not yet installed, install [Docker Engine](https://docs.docker.com/engine/install/). You may follow the [post installation steps](https://docs.docker.com/engine/install/linux-postinstall/) so that you do not need to use sudo, but be aware this opens up privilege escalation from your user. Included below:
```
sudo usermod -aG docker $USERNAME
#new shell or log out and then login
newgrp docker
```
Create a configuration file for the experiment. It is recommended to just use ```data/farmconfig.ini```. Only parameters that present in ```data/farmconfig.ini``` are currently modifiable. Note that the configuration files need to be located in the ```data``` directory or they will not sync with the container properly. Afterwards, export the config location:
```export CONFIG_PATH=data/farmconfig.ini```
Note that this will have to be performed again after restarting the terminal session.

**Before running, be aware that the container mounts to ```./workspace``` on the host, this directory will be overwritten.**
**Ensure that the iCEFARM system is already running - setup instructions [here](https://github.com/evolvablehardware/iCEFARM)**.

BitstreamEvolution can now be run:
```docker compose -f docker/bitstream.yml up --force-recreate```

Pressing `d` will detach from the output and the container will continue to run in the background. You can first get the name of the container with `docker container ls` and then run `docker logs <container name>` to view logs after detaching.

If you make a modification (not including config or seed file changes), you must add the ```--build``` flag to rebuild the image and apply changes.

Stopping the container:
```docker compose -f docker/bitstream.yml down```

If you wish to use a local version of the iCEFARM client instead of the one located in pypi, you can use the ```docker/bitstream_local.yml``` compose file instead. This requires an iCEFARM repository located at `/usr/local/lib/iCEFARM`.

#### Viewing live plots from a container

Since the container has no display server, matplotlib cannot open windows directly.

The compose file automatically mounts the container's `workspace/` directory to your host so that log files appear in real time, allowing `PlotEvolutionLive.py` to update continuously on your machine.

**1. Install the plotting dependencies on your host.** Only `matplotlib` and `numpy` are required (the other project dependencies are not needed):
```bash
pip install matplotlib numpy
```

**2. In a separate terminal, start the plotting script on your host:**
```bash
python3 src/PlotEvolutionLive.py
```

The plots will read from `workspace/` and auto-refresh every few seconds as new generations complete. You can leave this running for the duration of the experiment.

In some cases the file permissions may get messed up. If `PlotEvolutionLive` encounters an permission error for `workspace/plots`, you can fix it with the following:
`sudo chown $USER workspace/plots`

### Issues with setup:
This section describes some issues that can be encountered during
installation and how to address them. If the following steps do not
address your issue or you encounter other problems, please file an issue
[here](https://github.com/evolvablehardware/BitstreamEvolution/issues) so that
we can look into it.

## Usage
This section describes how to run the configure and run
BitstreamEvolution. For the most part, BitstreamEvolution can be run
as-is without configuration.

<!--
  TODO Configuration options that need to be changed should be
  better highlighted and emphasized. Ideally, the program would ensure
  that the user has set these before running (and they would be unset by
  default
-->
### Configuration
The project has various configuration options that can be specified in
`data/farmconfig.ini`. The file`data/default_config.ini` contains the
default options for the configuration and should not be modified.

See [CONFIG.md](./CONFIG.md) for a list of configuration options and their possible values.

### Running
From the root directory of BitstreamEvolution run:

```bash
python3 src/evolve.py -c data/farmconfig.ini
```

| Options | Description |
|-----------|-------------|
| -c | The config file this experiment uses |
| -d | The experiment description |
| -o | The output directory to store in the workspace in |

BitstreamEvolution will begin to run and display information in separate windows
that will appear (unless these have been disabled in the configuration).

BitstreamEvolution will continue to run until one of the following happens:
  * It has run through the specified number of generations
  * It has met the specified conditions
  * It is terminated in some other form (e.g. ctrl-c, shutdown, etc.)

### Running Test Cases
Test case files are simple to run using the pytest framework.
To run the entire suite:
```bash
pytest "test/"
```
You can also specify the desired file to run:
```bash
pytest "test/test_config_builder.py"
```
Alternatively, you can run individual tests within a file like so:'
```bash
pytest "test/file.py::function"
```

## Tools
### Generation Reconstruction
The code will automatically save each generation to a generation file in the generations directory (which is specified in the config)

You can later reconstruct generations. This will bring the generation back into your ASC directory. This is done by running `python3 src/tools/reconstruct.py [generation #]`

### Pulse Count Histogram
You can view a histogram of pulse counts for an entire experiment or particular generations using the pulse count histogram tool. Simply run `python3 src/tools/pulse_histogram.py`, and it will show the results for the last-run experiment (pulling from `workspace/pulselivedata.log`). A negative pulse count indicates the the microcontroller timed out five times in a row, and so no reading was recorded.

## Contributing
<!--TODO ALIFE2021 define the desired approach -->
Join the movement! Email derek.whitley1@gmail.com to get added to the Slack group.

## License
This project is licensed under the GNU GPL v3 or later. For more
information see [LICENSE](LICENSE).
