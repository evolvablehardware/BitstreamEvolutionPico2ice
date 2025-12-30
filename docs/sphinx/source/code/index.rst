===============
Refactored Code
===============

.. todo::
    Fix DEPENDANCY ANNOYANCE: 
    Have to do this so imports in the files work, 
    because they are evaluated relative to the home directory when python runs, 
    but relative to path directory when sphinx runs.

    This could be solved by always running from one directory, but it would mean that imports would be messed up if you decided not to run from that directory.
    One could also write a script to always add the base directory to the path whenever you run a file, but that is quite a bother.

    Discuss this.

    This is mostly a problem because sphinx must be provided a path and must be able to perform the needed imports, and providing multiple paths risks having names overlap so is undesireable.

.. toctree::
    :maxdepth: 2
    
    Circuit/index.rst
    EvaluateFitness/index.rst
    GenerateMeasurements/index.rst
    Hardware/index.rst
    Individual/index.rst
    Population/index.rst
    BitstreamEvolutionProtocols.rst
    TrivialImplementation.rst
    Directories.rst
    Evolution.rst
    Logger.rst
    PlotConfig.rst
    PlotDataRecorder.rst
    PlotEvolutionLive.rst
    utilities.rst
    

==========================
Documentation of Old Tools
==========================

.. toctree::
    tools/pulse_histogram
    tools/reconstruct