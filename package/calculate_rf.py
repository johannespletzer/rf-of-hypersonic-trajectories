"""First the imports are done and then the class code starts."""

from os import path

from pandas import DataFrame, merge, to_numeric
from aerocalc3.std_atm import alt2press
from scipy.interpolate import interp1d
from xarray import open_dataset
from numpy import insert, diff
from scipy.io import loadmat

from package.calculate_area import calculate_area as ca


class EmissionInventory:
    """The class contains multiple functions to calculate the radiative forcing
    of trace gases emitted up to 40 km. The calculations are based on pandas data structure.
    It is highly recommended to use the mask of tropospheric emission, since
    calculations are interpolated for altitudes from 30-38 km and extrapolated´
    for all others, which potentially introduces a large error."""

    def __init__(self, filepath):

        self.filepath = filepath

        self.resources_dir = path.join(path.dirname(__file__), "resources")

        self.load_sensitivities()

        if self.filepath.endswith(".mat"):
            self.data = self.load_mat_as_dataframe()
        elif self.filepath.endswith(".nc"):
            self.data = self.load_nc_as_dataframe()
        else:
            file_format = self.filepath.split(".")[-1]
            raise OSError(f"Unknown format: {file_format}")

    def load_sensitivities(self):
        """Load radiative sensitivities calculated with numerical climate model
        from file and store as lists"""

        with open(self.resources_dir + "/rf_sensitivities.txt", encoding="UTF-8") as f:
            self.rf_sens = [[float(x) for x in line.split(",")] for line in f]

        # sensitivities for outer edges and mid points of latitude regions
        self.lat_mid_point = self.rf_sens[0]
        self.o3_rf_at_30_km_for_h2 = self.rf_sens[1]
        self.o3_rf_at_38_km_for_h2 = self.rf_sens[2]
        self.o3_rf_at_30_km_for_h2o = self.rf_sens[3]
        self.o3_rf_at_38_km_for_h2o = self.rf_sens[4]
        self.o3_rf_at_30_km_for_no = self.rf_sens[5]
        self.o3_rf_at_38_km_for_no = self.rf_sens[6]
        self.h2o_rf_at_30_km_for_h2o = self.rf_sens[7]
        self.h2o_rf_at_38_km_for_h2o = self.rf_sens[8]

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

        data_frame = data_frame[data_frame[["H2 [kg]", "H2O [kg]", "NO [kg]"]].sum(axis=1) != 0]

        # filter final DataFrame
        data_frame.drop(["Altitude [ft]","H2O","H2","NO","dt"], axis=1, inplace=True)

        data_frame = data_frame.apply(to_numeric, downcast="float", errors="coerce")

        return data_frame

    def load_nc_as_dataframe(self):
        """This function creates a DataFrame from a netcdf file and selects certain variables."""

        nc_file = open_dataset(self.filepath).mean("time")

        # calculate height, area and volume of boxes
        km = nc_file.alt * 0.3048 / 1000
        nc_file = nc_file.assign_coords({'km':km})
        
        boxh = diff(insert(nc_file.km.values,0,0))
        nc_file = nc_file.assign_coords({'boxheight':("alt",boxh)})
        
        nc_file["Area [km2]"] = ca(nc_file.lat, nc_file.lon) / 1e6
        nc_file["Volume [km3]"] = nc_file["Area [km2]"] * nc_file.boxheight
        
        # calculate pressure levels
        pa = [alt2press(km, alt_units="km", press_units="pa") for km in nc_file.km.values]
        nc_file = nc_file.assign_coords({'Altitude [Pa]': ("alt",pa)})
        
        nc_file["H2O [kg]"] = nc_file["H2O"] * nc_file["Volume [km3]"]
        
        nc_file["H2 [kg]"] = nc_file["H2"] * nc_file["Volume [km3]"]
        
        nc_file["NO [kg]"] = nc_file["NO"] * nc_file["Volume [km3]"]
        
        nc_file = nc_file.drop_vars(["boxheight","Area [km2]","distkm","Fuel","H2","NO","H2O"])
        
        data_frame = nc_file.to_dataframe()
        
        # increase calculation speed by removing rows with zero emission
        data_frame = data_frame[data_frame[["H2 [kg]", "H2O [kg]", "NO [kg]"]].sum(axis=1) != 0]
        data_frame.reset_index(inplace=True)
        
        # rename columns
        columns = [
            "Altitude [ft]",
            "Latitude",
            "Longitude",
            "Altitude [km]",
            "Volume [km3]",
            "Altitude [Pa]",
            "H2O [kg]",
            "H2 [kg]",
            "NO [kg]",
        ] 
        
        data_frame.columns = columns

        data_frame.drop(["Volume [m3]"], axis=1, inplace=True)

        data_frame = data_frame.apply(to_numeric, downcast="float", errors="coerce")

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

            idx = self.data[["Latitude", "Longitude", "Altitude [km]"]].set_index(
                ["Latitude", "Longitude", "Altitude [km]"]
            )

            idx.index.rename(["lat", "lon", "alt"], inplace=True)

            merged_idx = merge(
                tropopause, idx, how="outer", left_index=True, right_index=True
            )

            tropopause_reidx = tropopause.reindex_like(merged_idx)
            tropopause_reidx = (
                tropopause_reidx.interpolate().reindex_like(idx).reset_index()
            )

            tropopause_reidx.columns = [
                "Latitude",
                "Longitude",
                "Altitude [km]",
                "tp_WMO [Pa]",
            ]

            self.data = merge(
                tropopause_reidx,
                self.data,
                left_on=["Latitude", "Longitude", "Altitude [km]"],
                right_on=["Latitude", "Longitude", "Altitude [km]"],
            )

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

        # calculate individual radiative forcings
        self.h2o_rf_from_h2o_emis()
        self.o3_rf_from_h2o_emis()
        self.o3_rf_from_h2_emis()
        self.o3_rf_from_no_emis()

        # calculate net of all individual radiative forcings
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

        # calculate individual radiative forcings
        self.o3_rf_from_h2o_emis()
        self.o3_rf_from_h2_emis()
        self.o3_rf_from_no_emis()

        # calculate net of all individual o3 radiative forcings
        net = (
            self.data["O3 RF from H2O [mW m-2]"].sum()
            + self.data["O3 RF from H2 [mW m-2]"].sum()
            + self.data["O3 RF from NO [mW m-2]"].sum()
        )

        return net

    def total_h2o_rf(self):
        """This function returns the net radiative forcing
        from water vapour (H2O emission)."""

        # calculate individual radiative forcings
        self.h2o_rf_from_h2o_emis()

        # calculate net of all individual h2o radiative forcings
        net = self.data["H2O RF from H2O [mW m-2]"].sum()

        return net

    def total_emis(self):
        """This function returns a list of the mass emissioni
        in tons (H2O, H2, NO) for the selected altitude."""

        # calculate mass emission
        h2o_emis = round(self.data["H2O [kg]"].sum() / 1e3, 2)
        h2_emis = round(self.data["H2 [kg]"].sum() / 1e3, 2)
        no_emis = round(self.data["NO [kg]"].sum() / 1e3, 2)

        return [h2o_emis, h2_emis, no_emis]
