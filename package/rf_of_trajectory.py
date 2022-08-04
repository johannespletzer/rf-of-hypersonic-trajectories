"""First the imports are done and then the class code starts."""

from os import path

from numpy import nan
from pandas import DataFrame, concat, to_numeric
from scipy.interpolate import interp1d
from scipy.io import loadmat
from xarray import open_dataset


class RadiativeForcingTrajectory:
    """The class contains multiple functions to calculate the radiative forcing
    of a .mat aircraft trajectory file. First developed by Johannes Pletzer (DLR)
    for Daniel Bodmer (TUHH). The calculations are based on pandas data structure.
    It is highly recommended to use the mask of tropospheric emission, since
    calculations are interpolated for altitudes from 30-38 km and extrapolated´
    for all others, which potentially introduces a large error."""

    def __init__(self, filepath):
        self.filepath = filepath

        self.resources_dir = path.join(path.dirname(__file__), "resources")

        self.o3_rf_at_30_km_for_h2 = [
            -3.04,
            -3.04,
            -3.04,
            -2.46,
            -2.46,
            -2.13,
            -1.75,
            -1.75,
        ]
        self.o3_rf_at_38_km_for_h2 = [
            -3.81,
            -3.81,
            -3.81,
            -2.59,
            -2.59,
            -2.72,
            -2.46,
            -2.46,
        ]

        self.o3_rf_at_30_km_for_h2o = [
            -0.20,
            -0.20,
            -0.20,
            -0.08,
            -0.08,
            -0.12,
            -0.12,
            -0.12,
        ]
        self.o3_rf_at_38_km_for_h2o = [
            -0.19,
            -0.19,
            -0.19,
            -0.07,
            -0.07,
            -0.09,
            -0.13,
            -0.13,
        ]

        self.o3_rf_at_30_km_for_no = [
            127.0,
            127.0,
            127.0,
            129.9,
            129.9,
            91.6,
            69.9,
            69.9,
        ]
        self.o3_rf_at_38_km_for_no = [102.9, 102.9, 102.9, 48.2, 48.2, 66.9, 74.3, 74.3]

        self.h2o_rf_at_30_km_for_h2o = [1.70, 1.70, 1.70, 1.90, 1.90, 1.65, 1.34, 1.34]
        self.h2o_rf_at_38_km_for_h2o = [1.89, 1.89, 1.89, 1.97, 1.97, 1.82, 1.59, 1.59]

    def load_trajectory_as_dataframe(self):
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
        self.data = data_frame

        return data_frame

    def horizontal_interp(self, val_30_km, val_38_km, var_30km, var_38km):
        """This function interpolates input values to latitude of
        DataFrame columns. Beware to use to the correct input."""

        data_ = self.data.copy()

        # outer edges and mid points of latitude regions
        lat_mid_point = [-90, -75, -45, -15, 15, 45, 75, 90]

        # define interpolation functions (linear, cubic)

        func_30_polar = interp1d(lat_mid_point, val_30_km, kind="linear")
        func_30_tropic = interp1d(lat_mid_point, val_30_km, kind="cubic")

        func_38_polar = interp1d(lat_mid_point, val_38_km, kind="linear")
        func_38_tropic = interp1d(lat_mid_point, val_38_km, kind="cubic")

        # linear interp. above 45° N, S; cubic below 45° N, S
        data_[var_30km] = data_["Latitude"].apply(
            lambda x: func_30_tropic(x) if abs(x) <= 45 else func_30_polar(x)
        )
        data_[var_38km] = data_["Latitude"].apply(
            lambda x: func_38_tropic(x) if abs(x) <= 45 else func_38_polar(x)
        )

        return data_

    def vertical_interp(self, data, var):
        """This function linearly inter- and extrapolates variable
        to altitude of DataFrame columns."""

        data_ = data.copy()

        # create columns with 30 and 38 km as x values for interpolation
        data_["30 km"] = 30
        data_["38 km"] = 38

        # apply linear interpolation
        data_[var] = data_.apply(
            lambda column: interp1d(
                [column["30 km"], column["38 km"]],
                [column[var + " [30 km]"], column[var + " [38 km]"]],
                fill_value="extrapolate",
            )(column["Altitude [km]"]),
            axis=1,
        )

        # clean data_Frame, remove variables
        data_.drop(
            ["30 km", "38 km", var + " [30 km]", var + " [38 km]"], axis=1, inplace=True
        )

        return data_

    def remove_emission_normalization(self, data, emis, var):
        """This function calculates total values of emission weighted variables."""

        data_ = data.copy()

        data_[var + " / kg"] = data_[var + " / Tg"] / 1e9  # Tg to kg
        data_["new_col"] = data_[var + " / kg"] * data_[emis]

        return data_["new_col"]

    def mask_troposphere(self, data, variable):
        """This function sets variable values, where the
        altitude is below the tropopause, to NaN."""

        data_ = data.copy()

        # load tropopause variable tp_WMO as pandas series

        tropause = open_dataset(
            self.resources_dir + "/STRATOFLY_1.0_SC0_X_tp-T42L90MA_X-X.nc"
        )
        tropause = tropause.mean("timem").tp_WMO.to_series()

        # get index from trajectory data_
        idx = data_[["Latitude", "Longitude"]].set_index(["Latitude", "Longitude"])
        idx.index.rename(["lat", "lon"], inplace=True)

        # reindex and interpolate tropopause data_ to trajectory index
        data_["tp_WMO"] = (
            tropause.reindex(tropause.index.union(idx.index))
            .interpolate()
            .reindex_like(idx)
            .values
        )

        # mask data_ below tropopause, drop tropopause variable
        data_.loc[(data_["Altitude [Pa]"] > data_["tp_WMO"]), variable] = nan
        data_.drop(["tp_WMO"], axis=1, inplace=True)

        return data_[variable]

    def drop_vertical_levels(self, alt=True):
        """This function removes rows, where the altitude is below
        the tropopause or another altitude. Input value has to be
        in hectopascal. Default is below the tropopause."""

        data_ = self.data.copy()

        if alt:
            # load tropopause variable tp_WMO as pandas series
            tropause = open_dataset(
                self.resources_dir + "/STRATOFLY_1.0_SC0_X_tp-T42L90MA_X-X.nc"
            )
            tropause = tropause.mean("timem").tp_WMO.to_series()

            # get index from trajectory data_
            idx = data_[["Latitude", "Longitude"]].set_index(["Latitude", "Longitude"])
            idx.index.rename(["lat", "lon"], inplace=True)

            # reindex and interpolate tropopause data_ to trajectory index
            data_["tp_WMO"] = (
                tropause.reindex(tropause.index.union(idx.index))
                .interpolate()
                .reindex_like(idx)
                .values
            )

            # drop data_ below tropopause, drop tropopause variable
            data_ = data_.drop(data_[data_["Altitude [Pa]"] > data_["tp_WMO"]].index)
        else:
            # drop data below altitude
            data_ = data_.drop(data_[data_["Altitude [Pa]"] > alt * 100].index)
        self.data = data_

        return data_

    def o3_rf_from_h2o_emis(self):
        """This function calculates the ozone radiative
        forcing due to water vapour emission."""

        data_ = self.data.copy()

        # use interp and weight functions
        data_ = self.horizontal_interp(
            self.o3_rf_at_30_km_for_h2o,
            self.o3_rf_at_38_km_for_h2o,
            "RF / Tg [30 km]",
            "RF / Tg [38 km]",
        )
        data_ = self.vertical_interp(data_, "RF / Tg")

        # calculate radiative forcing
        data_["O3 RF [mW m-2]"] = self.remove_emission_normalization(
            data_, "H2O [kg]", "RF"
        )
        data_.drop(["RF / Tg"], axis=1, inplace=True)

        # clean and set dtype
        data_ = data_.apply(to_numeric, downcast="float", errors="coerce")

        return data_

    def h2o_rf_from_h2o_emis(self):
        """This function calculates the water vapour radiative
        forcing due to water vapour emission."""

        data_ = self.data.copy()

        # use interp and weight functions
        data_ = self.horizontal_interp(
            self.h2o_rf_at_30_km_for_h2o,
            self.h2o_rf_at_38_km_for_h2o,
            "RF / Tg [30 km]",
            "RF / Tg [38 km]",
        )
        data_ = self.vertical_interp(data_, "RF / Tg")

        # radiative forcing
        data_["H2O RF [mW m-2]"] = self.remove_emission_normalization(
            data_, "H2O [kg]", "RF"
        )
        data_.drop(["RF / Tg"], axis=1, inplace=True)

        # clean and set dtype
        data_ = data_.apply(to_numeric, downcast="float", errors="coerce")

        return data_

    def o3_rf_from_h2_emis(self):
        """This function calculates the ozone radiative forcing due to hydrogen emission."""

        data_ = self.data.copy()

        # use interp and weight functions
        data_ = self.horizontal_interp(
            self.o3_rf_at_30_km_for_h2,
            self.o3_rf_at_38_km_for_h2,
            "RF / Tg [30 km]",
            "RF / Tg [38 km]",
        )
        data_ = self.vertical_interp(data_, "RF / Tg")

        # calculate radiative forcing
        data_["O3 RF [mW m-2]"] = self.remove_emission_normalization(
            data_, "H2 [kg]", "RF"
        )
        data_.drop(["RF / Tg"], axis=1, inplace=True)

        # clean and set dtype
        data_ = data_.apply(to_numeric, downcast="float", errors="coerce")

        return data_

    def o3_rf_from_no_emis(self):
        """This function calculates the ozone radiative
        forcing due to nitrogen oxide emission."""

        data_ = self.data.copy()

        # use interp and weight functions
        data_ = self.horizontal_interp(
            self.o3_rf_at_30_km_for_no,
            self.o3_rf_at_38_km_for_no,
            "RF / Tg [30 km]",
            "RF / Tg [38 km]",
        )
        data_ = self.vertical_interp(data_, "RF / Tg")

        # calculate radiative forcing
        data_["O3 RF [mW m-2]"] = self.remove_emission_normalization(
            data_, "NO [kg]", "RF"
        )
        data_.drop(["RF / Tg"], axis=1, inplace=True)

        # clean and set dtype
        data_ = data_.apply(to_numeric, downcast="float", errors="coerce")

        return data_

    def total_rf(self):
        """This function returns the net radiative forcing from ozone
        (H2O, H2, NO emission) and water vapour (H2O emission)."""

        # calculate radiative forcings for each point of trajectory
        data_frame_h2o = concat(
            [
                self.h2o_rf_from_h2o_emis(),
                self.o3_rf_from_h2o_emis()[["O3 RF [mW m-2]"]],
            ],
            axis=1,
        )
        data_frame_h2 = self.o3_rf_from_h2_emis()
        data_frame_no = self.o3_rf_from_no_emis()

        # Calculate net of all individual radiative forcings
        net = (
            data_frame_h2o["H2O RF [mW m-2]"].sum()
            + data_frame_h2o["O3 RF [mW m-2]"].sum()
            + data_frame_h2["O3 RF [mW m-2]"].sum()
            + data_frame_no["O3 RF [mW m-2]"].sum()
        )

        return net

    def total_o3_rf(self):
        """This function returns the net radiative forcing
        from ozone (H2O, H2, NO emission)."""

        # calculate radiative forcings for each point of trajectory
        data_frame_h2o = self.o3_rf_from_h2o_emis()
        data_frame_h2 = self.o3_rf_from_h2_emis()
        data_frame_no = self.o3_rf_from_no_emis()

        # Calculate net of all individual o3 radiative forcings
        net = (
            data_frame_h2o["O3 RF [mW m-2]"].sum()
            + data_frame_h2["O3 RF [mW m-2]"].sum()
            + data_frame_no["O3 RF [mW m-2]"].sum()
        )

        return net

    def total_h2o_rf(self):
        """This function returns the net radiative forcing
        from water vapour (H2O emission)."""

        # calculate radiative forcings for each point of trajectory
        data_frame_h2o = self.h2o_rf_from_h2o_emis()

        # Calculate net of all individual h2o radiative forcings
        net = data_frame_h2o["H2O RF [mW m-2]"].sum()

        return net

    def total_emis(self):
        """This function returns a list of the mass emissioni
        in tons (H2O, H2, NO) for the selected altitude."""

        data_ = self.data.copy()

        # Calculate mass emission
        h2o_emis = round(data_["H2O [kg]"].sum() / 1e3, 2)
        h2_emis = round(data_["H2 [kg]"].sum() / 1e3, 2)
        no_emis = round(data_["NO [kg]"].sum() / 1e3, 2)

        return [h2o_emis, h2_emis, no_emis]
