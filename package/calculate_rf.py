"""First the imports are done and then the class code starts."""

from os import path

from package.calculate_area import calculate_area as ca
from pandas import DataFrame, to_numeric, merge
from aerocalc3.std_atm import alt2press
from scipy.interpolate import interp1d
from scipy.io import loadmat
from xarray import open_dataset


class RadiativeForcing:
    """The class contains multiple functions to calculate the radiative forcing
    of trace gases emitted up to 40 km. The calculations are based on pandas data structure.
    It is highly recommended to use the mask of tropospheric emission, since
    calculations are interpolated for altitudes from 30-38 km and extrapolated´
    for all others, which potentially introduces a large error."""

    def __init__(self, filepath):
        
        self.filepath = filepath

        self.resources_dir = path.join(path.dirname(__file__), "resources")

        # outer edges and mid points of latitude regions
        self.lat_mid_point = [-90, -75, -45, -15, 15, 45, 75, 90]

        # sensitivities for outer edges and mid points of latitude regions
        self.o3_rf_at_30_km_for_h2 = [-3.04, -3.04, -3.04, -2.46, -2.46, -2.13, -1.75, -1.75]

        self.o3_rf_at_38_km_for_h2 = [-3.81, -3.81, -3.81, -2.59, -2.59, -2.72, -2.46, -2.46]

        self.o3_rf_at_30_km_for_h2o = [-0.20, -0.20, -0.20, -0.08, -0.08, -0.12, -0.12, -0.12]

        self.o3_rf_at_38_km_for_h2o = [-0.19, -0.19, -0.19, -0.07, -0.07, -0.09, -0.13, -0.13]

        self.o3_rf_at_30_km_for_no = [127.0, 127.0, 127.0, 129.9, 129.9, 91.6, 69.9, 69.9]

        self.o3_rf_at_38_km_for_no = [102.9, 102.9, 102.9, 48.2, 48.2, 66.9, 74.3, 74.3]

        self.h2o_rf_at_30_km_for_h2o = [1.70, 1.70, 1.70, 1.90, 1.90, 1.65, 1.34, 1.34]

        self.h2o_rf_at_38_km_for_h2o = [1.89, 1.89, 1.89, 1.97, 1.97, 1.82, 1.59, 1.59]
        
        if self.filepath.endswith('.mat'):
            self.data = self.load_mat_as_dataframe()
        elif self.filepath.endswith('.nc'):
            self.data = self.load_nc_as_dataframe()
        else:
            raise OSError('Unknown format: %r' % (self.filepath.split('.')[-1]))
                

    def load_mat_as_dataframe(self):
        """This function creates a DataFrame from a MatLab file and selects certain variables."""

        mat = loadmat(self.filepath, squeeze_me=True)

        new_data = list(
            zip(
                mat["Trajectory"]["poslon"],
                mat["Trajectory"]["poslat"],
                mat["Trajectory"]["altft"],
                mat["Trajectory"]["pressure"],
                mat["Trajectory"]["H2O"],
                mat["Trajectory"]["H2"],
                mat["Trajectory"]["NO"],
                mat["Trajectory"]["ST"],
            )
        )

        columns = [
            "Longitude",
            "Latitude",
            "Altitude [ft]",
            "Altitude [Pa]",
            "H2O",
            "H2",
            "NO",
            "dt",
        ]

        data_frame = DataFrame(new_data, columns=columns)

        # transform altitude from ft to km
        data_frame["Altitude [km]"] = data_frame["Altitude [ft]"] * 0.3048 / 1000

        # normalize emission with duration at flight path
        data_frame["H2O [kg]"] = data_frame["H2O"] * data_frame["dt"] / 1000
        data_frame["NO [kg]"] = data_frame["NO"] * data_frame["dt"] / 1000
        data_frame["H2 [kg]"] = data_frame["H2"] * data_frame["dt"] / 1000

        # select final DataFrame
        data_frame = data_frame[
            [
                "Latitude",
                "Longitude",
                "Altitude [km]",
                "Altitude [Pa]",
                "H2O [kg]",
                "NO [kg]",
                "H2 [kg]",
            ]
        ]
        data_frame = data_frame.apply(to_numeric, downcast="float", errors="coerce")

        return data_frame
    
    def load_nc_as_dataframe(self):
        """This function creates a DataFrame from a netcdf file and selects certain variables."""

        nc = open_dataset(self.filepath)
        
        nc['Area [km2]'] = ca(nc.lon,nc.lat) / 1e6
        
        data_frame = nc.to_dataframe()
        
        # Increase calculation speed by removing rows with zero emission
        data_frame = data_frame[data_frame[['H2','H2O','NO']].sum(axis=1) != 0]
        data_frame.reset_index(inplace=True)
        
        columns = [
                    "time",
                    "Altitude [ft]",
                    "Latitude",
                    "Longitude",
                    "H2 [kg/km3]",
                    "NO [kg/km3]",
                    "H2O [kg/km3]",
                    "Fuel",
                    "distkm",
                    "Area [km2]"
                ]

        data_frame.columns = columns

        # Altitude calculations
        data_frame["Altitude [km]"] = data_frame["Altitude [ft]"] * 0.3048 / 1000
        data_frame['Altitude [Pa]'] = data_frame['Altitude [km]'].map(lambda km: alt2press(km, alt_units='km', press_units='pa'))
        
        # Grid calculations
        data_frame["Volume [km3]"] = data_frame["Altitude [km]"] * data_frame["Area [km2]"]
        
        # Mass calculations
        data_frame["H2 [kg]"] = data_frame["H2 [kg/km3]"] * data_frame["Volume [km3]"]
        data_frame["H2O [kg]"] = data_frame["H2O [kg/km3]"] * data_frame["Volume [km3]"]
        data_frame["NO [kg]"] = data_frame["NO [kg/km3]"] * data_frame["Volume [km3]"]

        # Final DataFrame
        data_frame = data_frame[['Latitude', 'Longitude', 'Altitude [km]', 'Altitude [Pa]', 'H2 [kg]', 'H2O [kg]', 'NO [kg]']]

        return data_frame

    def horizontal_interp(self, val_30_km, val_38_km, var_30km, var_38km):
        """This function interpolates input values to latitude of
        DataFrame columns. Beware to use to the correct input."""

        # define interpolation functions (linear, cubic)

        func_30_polar = interp1d(self.lat_mid_point, val_30_km, kind="linear")
        func_30_tropic = interp1d(self.lat_mid_point, val_30_km, kind="cubic")

        func_38_polar = interp1d(self.lat_mid_point, val_38_km, kind="linear")
        func_38_tropic = interp1d(self.lat_mid_point, val_38_km, kind="cubic")

        # linear interp. above 45° N, S; cubic below 45° N, S
        self.data[var_30km] = self.data["Latitude"].apply(
            lambda x: func_30_tropic(x) if abs(x) <= 45 else func_30_polar(x)
        )
        self.data[var_38km] = self.data["Latitude"].apply(
            lambda x: func_38_tropic(x) if abs(x) <= 45 else func_38_polar(x)
        )

    def vertical_interp(self, var):
        """This function linearly inter- and extrapolates variable
        to altitude of DataFrame columns."""

        # create columns with 30 and 38 km as x values for interpolation
        self.data["30 km"] = 30
        self.data["38 km"] = 38

        # apply linear interpolation
        self.data[var] = self.data.apply(
            lambda column: interp1d(
                [column["30 km"], column["38 km"]],
                [column[var + " [30 km]"], column[var + " [38 km]"]],
                fill_value="extrapolate",
            )(column["Altitude [km]"]),
            axis=1,
        )

        # clean DataFrame, remove variables
        self.data.drop(
            ["30 km", "38 km", var + " [30 km]", var + " [38 km]"], axis=1, inplace=True
        )

    def remove_emission_normalization(self, emis, var):
        """This function calculates total values of emission weighted variables."""

        new_col = self.data[var + " / Tg"] / 1e9  # Tg to kg
        new_col = new_col * self.data[emis]

        return new_col

    def drop_vertical_levels(self, alt=True):
        """This function removes rows, where the altitude is below
        the tropopause or another altitude. Input value has to be
        in hectopascal. Default is below the tropopause."""

        if alt is True:
            # load tropopause variable tp_WMO as pandas series
            tropopause = open_dataset(
                self.resources_dir + "/STRATOFLY_1.0_SC0_X_tp-T42L90MA_X-X.nc"
            )
            tropopause = tropopause.mean("timem").tp_WMO.to_series()

            idx = self.data[["Latitude", "Longitude", "Altitude [km]"]]\
                            .set_index(["Latitude", "Longitude", "Altitude [km]"])

            idx.index.rename(["lat", "lon", "alt"], inplace=True)

            merged_idx = merge(tropopause, idx, how='outer', left_index=True, right_index=True)

            tropopause_reidx = tropopause.reindex_like(merged_idx)
            tropopause_reidx = tropopause_reidx.interpolate().reindex_like(idx).reset_index()

            tropopause_reidx.columns = ["Latitude", "Longitude", "Altitude [km]", "tp_WMO [Pa]"]

            self.data = merge(tropopause_reidx, self.data
                              , left_on=["Latitude", "Longitude", "Altitude [km]"]
                              , right_on=["Latitude", "Longitude", "Altitude [km]"])

            # drop data below tropopause, drop tropopause variable
            self.data.drop(
                self.data[self.data["Altitude [Pa]"] > self.data["tp_WMO [Pa]"]].index,
                inplace=True,
            )
        else:
            # drop data below altitude
            self.data.drop(
                self.data[self.data["Altitude [Pa]"] > alt * 100].index, inplace=True
            )

    def o3_rf_from_h2o_emis(self):
        """This function calculates the ozone radiative
        forcing due to water vapour emission."""

        # use interp and weight functions
        self.horizontal_interp(
            self.o3_rf_at_30_km_for_h2o,
            self.o3_rf_at_38_km_for_h2o,
            "RF / Tg [30 km]",
            "RF / Tg [38 km]",
        )
        self.vertical_interp("RF / Tg")

        # calculate radiative forcing
        self.data["O3 RF from H2O [mW m-2]"] = self.remove_emission_normalization(
            "H2O [kg]", "RF"
        )
        self.data.drop(["RF / Tg"], axis=1, inplace=True)

        # clean and set dtype
        self.data.apply(to_numeric, downcast="float", errors="coerce")

    def h2o_rf_from_h2o_emis(self):
        """This function calculates the water vapour radiative
        forcing due to water vapour emission."""

        # use interp and weight functions
        self.horizontal_interp(
            self.h2o_rf_at_30_km_for_h2o,
            self.h2o_rf_at_38_km_for_h2o,
            "RF / Tg [30 km]",
            "RF / Tg [38 km]",
        )
        self.vertical_interp("RF / Tg")

        # radiative forcing
        self.data["H2O RF from H2O [mW m-2]"] = self.remove_emission_normalization(
            "H2O [kg]", "RF"
        )
        self.data.drop(["RF / Tg"], axis=1, inplace=True)

        # clean and set dtype
        self.data.apply(to_numeric, downcast="float", errors="coerce")

    def o3_rf_from_h2_emis(self):
        """This function calculates the ozone radiative forcing due to hydrogen emission."""

        # use interp and weight functions
        self.horizontal_interp(
            self.o3_rf_at_30_km_for_h2,
            self.o3_rf_at_38_km_for_h2,
            "RF / Tg [30 km]",
            "RF / Tg [38 km]",
        )
        self.vertical_interp("RF / Tg")

        # calculate radiative forcing
        self.data["O3 RF from H2 [mW m-2]"] = self.remove_emission_normalization(
            "H2 [kg]", "RF"
        )
        self.data.drop(["RF / Tg"], axis=1, inplace=True)

        # clean and set dtype
        self.data.apply(to_numeric, downcast="float", errors="coerce")

    def o3_rf_from_no_emis(self):
        """This function calculates the ozone radiative
        forcing due to nitrogen oxide emission."""

        # use interp and weight functions
        self.horizontal_interp(
            self.o3_rf_at_30_km_for_no,
            self.o3_rf_at_38_km_for_no,
            "RF / Tg [30 km]",
            "RF / Tg [38 km]",
        )
        self.vertical_interp("RF / Tg")

        # calculate radiative forcing
        self.data["O3 RF from NO [mW m-2]"] = self.remove_emission_normalization(
            "NO [kg]", "RF"
        )
        self.data.drop(["RF / Tg"], axis=1, inplace=True)

        # clean and set dtype
        self.data.apply(to_numeric, downcast="float", errors="coerce")

    def total_rf(self):
        """This function returns the net radiative forcing from ozone
        (H2O, H2, NO emission) and water vapour (H2O emission)."""

        # calculate radiative forcings for each point of trajectory
        self.h2o_rf_from_h2o_emis()
        self.o3_rf_from_h2o_emis()
        self.o3_rf_from_h2_emis()
        self.o3_rf_from_no_emis()

        # Calculate net of all individual radiative forcings
        net = (
            self.data["H2O RF from H2O [mW m-2]"].sum()
            + self.data["O3 RF from H2O [mW m-2]"].sum()
            + self.data["O3 RF from H2 [mW m-2]"].sum()
            + self.data["O3 RF from NO [mW m-2]"].sum()
        )

        return net

    def total_o3_rf(self):
        """This function returns the net radiative forcing
        from ozone (H2O, H2, NO emission)."""

        # calculate radiative forcings for each point of trajectory
        self.o3_rf_from_h2o_emis()
        self.o3_rf_from_h2_emis()
        self.o3_rf_from_no_emis()

        # Calculate net of all individual o3 radiative forcings
        net = (
            self.data["O3 RF from H2O [mW m-2]"].sum()
            + self.data["O3 RF from H2 [mW m-2]"].sum()
            + self.data["O3 RF from NO [mW m-2]"].sum()
        )

        return net

    def total_h2o_rf(self):
        """This function returns the net radiative forcing
        from water vapour (H2O emission)."""

        # calculate radiative forcings for each point of trajectory
        self.h2o_rf_from_h2o_emis()

        # Calculate net of all individual h2o radiative forcings
        net = self.data["H2O RF from H2O [mW m-2]"].sum()

        return net

    def total_emis(self):
        """This function returns a list of the mass emissioni
        in tons (H2O, H2, NO) for the selected altitude."""

        # Calculate mass emission
        h2o_emis = round(self.data["H2O [kg]"].sum() / 1e3, 2)
        h2_emis = round(self.data["H2 [kg]"].sum() / 1e3, 2)
        no_emis = round(self.data["NO [kg]"].sum() / 1e3, 2)

        return [h2o_emis, h2_emis, no_emis]
