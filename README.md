# omayabias
Bias Software for OMAyA

# Installation and setup Instructions

# Python VirtualEnv

Setup python virtual environment:

	virtualenv -p python3 venv
    source venv/bin/activate
	pip install -r requirements.txt

## Install Labjack LJM libraries

Find the installer for the LJM libraries at https://labjack.com/ljm
and unpack and follow instructions in INSTALL.md in that package.

## Install Python bindings for LJM

Find the installer for the Python LJM bindings at
https://labjack.com/support/software/examples/ljm/python 
Unzip the zip file, and from within the virtual environment do:

	python setup.py install

## Install Python bindings for U3 (used in LO system)

Find the python installer at: 
https://labjack.com/support/software/examples/ud/labjackpython
Unzip the zip file, and from within the virtual environment do:

	python setup.py install
	
## Development

After making changes in the omayabias source code, to install within
the virtual environment:

	python setup.py develop
	
