Run OPM Flow from Python
========================

To run OPM from Python, you need to:

1. Compile Flow with python support:

- Add the cmake flags -DOPM_ENABLE_PYTHON=ON and -DOPM_INSTALL_PYTHON=ON.
- Optionally add prefix -DCMAKE_INSTALL_PREFIX=/opt/opm to install outside the standard directories.
- Optionally specify python binary -DPython3_EXECUTABLE=/home/user/miniconda3/envs/rkt/bin/python3 if you don't want to use the system python, e.g. use a python from pyenv or from a conda environment.

Sample compilation on linux:

.. code-block:: bash

		#! /bin/bash

		flags="-DPython3_EXECUTABLE=/home/hakon/miniconda3/envs/rkt/bin/python3 -DOPM_ENABLE_PYTHON=ON -DOPM_INSTALL_PYTHON=ON -DCMAKE_INSTALL_PREFIX=/opt/opm"
		for repo in opm-common opm-grid opm-models opm-simulators
		do
		    cd "$repo"
		    mkdir -p build
		    cd build
		    cmake  $flags ..
		    make -j8
		    sudo make install
		    cd ..
		    cd ..
		done

2. Now you should be able to use the module from a Python script.

If you installed in a non-standard directory by specifying -DCMAKE_INSTALL_PREFIX you may need to set the PYTHONPATH environment variable before running your Python script, for example:

.. code-block:: bash

		PYTHONPATH=/opt/opm/lib/python3.11/site-packages python3 spe1case1.py

Here, the example script spe1case1.py could be:

.. code-block:: python

		from opm.simulators import BlackOilSimulator
		from opm.io.parser import Parser
		from opm.io.ecl_state import EclipseState
		from opm.io.schedule import Schedule
		from opm.io.summary import SummaryConfig

		deck  = Parser().parse('SPE1CASE1.DATA')
		state = EclipseState(deck)
		schedule = Schedule( deck, state )
		summary_config = SummaryConfig(deck, state, schedule)

		sim = BlackOilSimulator(deck, state, schedule, summary_config)
		sim.step_init()
		sim.step()
		poro = sim.get_porosity()
		poro = poro *.95
		sim.set_porosity(poro)
		sim.step()
		sim.step_cleanup()

where you could use the SPE1CASE1.DATA file from `the opm-test repository <https://github.com/OPM/opm-tests/tree/master/spe1>`_.
