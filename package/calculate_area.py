"""
The functions are part of another package (emacutils), which will be
published in the future. The original code was written by Mattia Righi
and partly changed by Johannes Pletzer.

Author: Mattia Righi (DLR, Germany).
"""

from numpy import append, deg2rad, insert, outer, sign, sin
from xarray import DataArray

EARTH_RADIUS = 6371000.0  # [m]

def guess_interfaces(coordinate):
    """
    Calculate the interfaces of a coordinate given its midpoints.

    Parameters
    ----------
    coordinate : array.DataArray
        The coordinate array.

    Returns
    -------
    xarray.DataArray
        An array with the size of the coordinate plus one.
    """

    interfaces = 0.5 * (coordinate.data[0:-1] + coordinate.data[1:])
    first = 0.5 * (3 * coordinate.data[0] - coordinate.data[1])
    last = 0.5 * (3 * coordinate.data[-1] - coordinate.data[-2])

    # Check limits
    if coordinate.name.lower() in ['lat', 'latitude']:
        first = sign(first) * min([abs(first), 90.])
        last = sign(last) * min([abs(last), 90.])

    interfaces = insert(interfaces, 0, first)
    interfaces = append(interfaces, last)

    return interfaces

def calculate_area(latitude, longitude):
    """
    Calculate the area of each grid cell on a regular lat-lon grid.

    Parameters
    ----------
    latitude : array.DataArray
        The latitude coordinate of the grid.

    longitude : xarray.DataArray
        The longitude coordinate of the grid.

    Returns
    -------
    xarray.DataArray
        An array with the area (in m2) and the input latitude and longitude as
        coordinates.
    """

    lat_i = deg2rad(guess_interfaces(latitude))
    lon_i = deg2rad(guess_interfaces(longitude))

    delta_x = abs(lon_i[1:] - lon_i[:-1])
    delta_y = abs(sin(lat_i[1:]) - sin(lat_i[:-1]))

    output = outer(delta_y, delta_x) * EARTH_RADIUS ** 2
    output = output.astype('float32')

    result = DataArray(output, name='area',
                       dims=(latitude.name, longitude.name),
                       coords={latitude.name: latitude,
                               longitude.name: longitude},
                       attrs={'units': 'm2'})

    return result
