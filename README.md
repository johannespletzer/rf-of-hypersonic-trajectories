# Radiative forcing of hypersonic aircraft trajectories
The repository provides a Python Class, an example and an executable to calculate the climate impact (stratosphere adjusted radiative forcing) of hypersonic aircraft trajectories. The radiative forcing of water vapour changes and ozone changes are calculated on the basis of water vapour, hydrogen and nitrogen oxide emissions. 

# Limitations
Interpolation (30-38 km) and extrapolation 0-30 km are used. It is recommended to note the following:
- The class includes a function that masks emission in the troposphere and excludes it from the climate calculation. Its use is strongly recommended.
- The climate impact of trajectories where the average flight altitude does not correspond to the typical hypersonic flight altitudes (about 24-40 km) should not be estimated.
- Meaningful results can be expected from the radiative effect of water vapour changes due to water vapour emissions. This explicitly excludes the radiative effect of water vapour changes due to hydrogen and nitrogen oxide emissions.
- Meaningful results can be expected from the radiative effect of ozone changes due to water vapour, hydrogen and nitrogen oxide emissions.

The atmospheric and radiative sensitivites are based on results from Pletzer et al (2023, in prep.).

# Python environment requirements
The software requires various functions from the following python modules:

- numpy
- pandas
- xarray
- scipy

# Getting started
The software currently only works with mat files. They have to be placed in the subfolder 'Data', which is extracted from the rf_of_trajectories.zip. The current main.py executable reads all trajectory files within 'Data' and returns the calculated radiative forcing in an xlsx file.
