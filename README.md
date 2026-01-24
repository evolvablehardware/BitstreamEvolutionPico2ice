# BitstreamEvolution + iCEFARM

## Configuring
- Set the ```USBIPICE_CONTROL``` environment variable to control server url. This is ```http://localhost:8080``` when running the iCEFARM compose stack.
- Set the ```USBIPICE_DEVICES``` environment variable to the amount of devices to use.
- Set the ```USBIPICE_MODE``` environment variable to either ```all``` or ```quick```. The ```all``` mode evaluates circuit fitness on each device and uses the minimum. The ```quick``` mode evaluates each circuit only once on a random device.
- See [```farmconfig.ini```](./farmconfig.ini) for an example config. This is the config used when running through Docker. Configuration values not present in this example config may produce unexpected behavior. Notably, an addition option has been added to ROUTING - ```ALL``` - which removes all row restraints.

## Running - locally
Set up BitstreamEvolution normally, install additional package:
```
pip install ascutil
```
Start the iCEFARM compose stack. Move ```1kz_ice27_generated.asc``` to ```data/seed-hardware.asc```. This is a 1kHz clock outputting on ice40 27/pico gpio 20 generated from verilog. Set the environment variables mentioned previously and specify the ```farmconfig.ini``` config. Start the iCEFARM compose stack. Run BitstreamEvolution normally:
```
python3 src/evolve.py -c farmconfig.ini
```

## Running - docker
Start the iCEFARM control stack. Set the environment variables mentioned previously and modify the config if desired. The docker image will automatically use the ```1kz_ice27_generated.asc``` seed. Build and run the image:
```
docker build -t bitstreamevolution .
docker run -it -e USBIPICE_CONTROL=$USBIPICE_CONTROL -e USBIPICE_DEVICES=$USBIPICE_DEVICES -e USBIPICE_MODE=$USBIPICE_MODE --network=host bitstreamevolution .venv/bin/python3 src/evolve.py -c farmconfig.ini -d desc
```
Note that after modifying the config file, the image will need to be rebuilt. The live plots will also not display. After/during the experiment, you can copy the workspace folder onto the host and manually run ```PlotEvolutionLive.py```.

## Fitness changes
The pulse count fitness function has been changed:
$$\frac{ \frac {1} {MSE(expected, actual)}} {1 + \sum max(|p-mean(P)| - 0.03*expected, 0)^2}$$