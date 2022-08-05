# Radiative forcing of hypersonic aircraft trajectories
The repository provides a Python Class, an example and an executable to calculate the climate impact (stratosphere adjusted radiative forcing) of hypersonic aircraft trajectories. The radiative forcing of water vapour changes and ozone changes are calculated on the basis of water vapour, hydrogen and nitrogen oxide emissions. 

# Limitations
Interpolation (30-38 km) and extrapolation 0-30 km are used. It is recommended to note the following:
- The class includes a function (`drop_vertical_levels()`) that drops emission in the troposphere or below specified altitude levels and excludes it from the climate calculation. Its use is strongly recommended.
- The climate impact of trajectories where the average flight altitude does not correspond to the typical hypersonic flight altitudes (about 24-40 km) should not be estimated.
- Meaningful results can be expected for the radiative effect of water vapour changes due to water vapour emissions. This explicitly excludes the radiative effect of water vapour changes due to hydrogen and nitrogen oxide emissions.
- Meaningful results can be expected for the radiative effect of ozone changes due to water vapour, hydrogen and nitrogen oxide emissions.

The atmospheric and radiative sensitivites are based on results from Pletzer et al (2023, in prep.).

# Python environment requirements
The software requires various functions from the following python modules:

- numpy
- pandas
- xarray
- scipy
- xlsxwriter
- netcdf4

Install the required packages with `pip install numpy pandas xarray scipy xlsxwriter netcdf4`.

# Getting started
The software currently only works with mat files. They have to be stored within one folder. The main.py executable reads all trajectory files within the folder and returns the calculated radiative forcing in an xlsx file. Execute main.py with `python3 main.py <path_to_your_trajectory_files>`.

# Code quality
The code was formatted according to PEP 8 style with the help of the modules 'flake8', 'isort', 'pylint' and 'black'.
