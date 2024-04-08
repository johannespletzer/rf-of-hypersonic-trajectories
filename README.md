# Radiative forcing of hypersonic aircraft emission inventories
The software quantifies climate impact of hypersonic aircraft emission inventories as a number and within seconds instead of very long numerical simulations that produce Petabytes of data. The input requires water vapor, hydrogen and nitrogen oxide emission data along flight trajectories.
The repository provides a Python package, examples and an executable to calculate the climate impact (stratosphere adjusted radiative forcing) of hypersonic aircraft emission inventories. The radiative forcing of water vapour changes and ozone changes are calculated on the basis of water vapour, hydrogen and nitrogen oxide emissions. The current version is able to read in mat- and nc-files. NetCDF read in is currently optimised for data published online, e.g. for the aircraft design [STRATOFLY-MR3](https://zenodo.org/records/10818082).

Latest software release: [![DOI](https://zenodo.org/badge/518852238.svg)](https://zenodo.org/badge/latestdoi/518852238)

# Limitations
Interpolation (30-38 km) and extrapolation surface-30 km are used. It is recommended to note the following:
- The atmospheric and radiative sensitivites are based on results from [Pletzer et al (2024)](https://acp.copernicus.org/articles/24/1743/2024/). The atmospheric composition of the numerical climate model is based on surface emission inventories for 2050. 
- The class includes a function (`drop_vertical_levels()`) that drops emission in the troposphere or below specified altitude levels and excludes it from the climate calculation. Its use is strongly recommended as long as sensitivities are not yet extended to altitudes below 30 km.
- The climate impact of emission inventories where the average flight altitude does not correspond to the typical hypersonic flight altitudes (about 24-40 km) should not be estimated.
- Meaningful results can be expected for the radiative effect of water vapour changes due to water vapour emissions. This explicitly excludes the radiative effect of water vapour changes due to hydrogen and nitrogen oxide emissions.
- Meaningful results can be expected for the radiative effect of ozone changes due to water vapour, hydrogen and nitrogen oxide emissions.

Please keep these limitations in mind when using the software.

# Python environment requirements
The software requires various functions from the following python modules:

- numpy
- pandas
- xarray
- scipy
- xlsxwriter
- netcdf4
- aerocalc3

Install the required packages with `pip install numpy pandas xarray scipy xlsxwriter netcdf4 aerocalc3`.

# Getting started
The repo contains two example notebooks for processing of emission inventories in mat- and nc-format. Otherwise, the user can run the main.py executable which reads all emission inventory files within the folder and returns the calculated radiative forcing in an xlsx file. Execute main.py with `python3 main.py <path_to_your_emission_files>`. Please contact Johannes Pletzer for any questions.

# Code quality
The code was formatted according to PEP 8 style with the help of the modules 'flake8', 'isort', 'pylint' and 'black'.

# Acknowledgements
Daniel Bodmer contributed with validation of model results by offering current state of the art hypersonic aircraft trajectories on aircraft and fleet level: [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.10818082.svg)](https://doi.org/10.5281/zenodo.10818082)


