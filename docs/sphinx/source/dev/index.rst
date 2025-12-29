---------
dev index
---------

Link To Main Website
--------------------

Here is a section that should be replaced on main website, and visible on the dev branch.

Here is the link to the main website:
`MAIN WEBSITE <https://evolvablehardware.github.io/BitstreamEvolution/index.html>`_


How To Create The Website Manually
----------------------------------

The Webiste will be generated automatically by Github Actions, but this section is meant to remind me how I can create this sphinx website manually on my local computer.


.. code-block:: bash
    :caption: Installing Poetry & Compiling Website
    
    cd BitstreamEvolution/docs/sphinx

    poetry install --with dev
    
    poetry run make html

    cd build/html

    open_in_web_browser index.html


