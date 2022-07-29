class rf_of_trajectory:
    """The class contains multiple functions to calculate the radiative forcing of a .mat aircraft trajectory file. First developed by Johannes Pletzer (DLR) for Daniel Bodmer (TUHH). The calculations are based on pandas data structure.It is highly recommended to use the mask of tropospheric emission, since calculations are interpolated for altitudes from 30-38 km and extrapolated for all others, which potentially introduces a large error."""

    def __init__(self, filepath):
        self.filepath = filepath

        from pandas import to_numeric

        self.to_numeric = to_numeric

    def load_trajectory_as_dataframe(self):
        """This function creates a DataFrame from a MatLab file and selects certain variables."""

        from scipy.io import loadmat
        from pandas import DataFrame

        mat = loadmat(self.filepath, squeeze_me=True)

        newData = list(
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

        df = DataFrame(newData, columns=columns)

        # transform altitude from ft to km
        df["Altitude [km]"] = df["Altitude [ft]"] * 0.3048 / 1000

        # normalize emission with duration at flight path
        df["H2O [kg]"] = df["H2O"] * df["dt"] / 1000
        df["NO [kg]"] = df["NO"] * df["dt"] / 1000
        df["H2 [kg]"] = df["H2"] * df["dt"] / 1000

        # select final DataFrame
        df = df[
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
        df = df.apply(self.to_numeric, downcast="float", errors="coerce")
        self.file = df

        return df

    def horizontal_interp(self, data, val_30_km, val_38_km, var1, var2):
        """This function interpolates input values to latitude of DataFrame columns."""

        from numpy import abs

        data_ = data.copy()

        # outer edges and mid points of latitude regions
        x = [-90, -75, -45, -15, 15, 45, 75, 90]

        # define interpolation functions (linear, cubic)
        from scipy.interpolate import interp1d

        func_30_polar = interp1d(x, val_30_km, kind="linear")
        func_30_tropic = interp1d(x, val_30_km, kind="cubic")

        func_38_polar = interp1d(x, val_38_km, kind="linear")
        func_38_tropic = interp1d(x, val_38_km, kind="cubic")

        # linear interp. above 45° N, S; cubic below 45° N, S
        data_[var1] = data_["Latitude"].apply(
            lambda x: func_30_tropic(x) if abs(x) <= 45 else func_30_polar(x)
        )
        data_[var2] = data_["Latitude"].apply(
            lambda x: func_38_tropic(x) if abs(x) <= 45 else func_38_polar(x)
        )

        return data_

    def vertical_interp(self, data, var):
        """This function linearly inter- and extrapolates variable to altitude of DataFrame columns."""

        data_ = data.copy()

        # create columns with 30 and 38 km as x values for interpolation
        data_["30 km"] = 30
        data_["38 km"] = 38

        # apply linear interpolation
        from scipy.interpolate import interp1d

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
        """This function sets variable values, where the altitude is below the tropopause, to NaN."""

        data_ = data.copy()

        # load tropopause variable tp_WMO as pandas series
        from numpy import nan
        from xarray import open_dataset

        tp = open_dataset("Data/STRATOFLY_1.0_SC0_X_tp-T42L90MA_X-X.nc")
        tp = tp.mean("timem").tp_WMO.to_series()

        # get index from trajectory data_
        idx = data_[["Latitude", "Longitude"]].set_index(["Latitude", "Longitude"])
        idx.index.rename(["lat", "lon"], inplace=True)

        # reindex and interpolate tropopause data_ to trajectory index
        data_["tp_WMO"] = (
            tp.reindex(tp.index.union(idx.index)).interpolate().reindex_like(idx).values
        )

        # mask data_ below tropopause, drop tropopause variable
        data_.loc[(data_["Altitude [Pa]"] > data_["tp_WMO"]), variable] = nan
        data_.drop(["tp_WMO"], axis=1, inplace=True)

        return data_[variable]

    def drop_vertical_levels(self, alt=True):
        """This function removes rows, where the altitude is below the tropopause or another altitude. Input value has to be in hectopascal. Default is below the tropopause."""

        data_ = self.file.copy()

        if alt is True:
            # load tropopause variable tp_WMO as pandas series
            from xarray import open_dataset

            tp = open_dataset("Data/STRATOFLY_1.0_SC0_X_tp-T42L90MA_X-X.nc")
            tp = tp.mean("timem").tp_WMO.to_series()

            # get index from trajectory data_
            idx = data_[["Latitude", "Longitude"]].set_index(["Latitude", "Longitude"])
            idx.index.rename(["lat", "lon"], inplace=True)

            # reindex and interpolate tropopause data_ to trajectory index
            data_["tp_WMO"] = (
                tp.reindex(tp.index.union(idx.index))
                .interpolate()
                .reindex_like(idx)
                .values
            )

            # drop data_ below tropopause, drop tropopause variable
            data_ = data_.drop(data_[data_["Altitude [Pa]"] > data_["tp_WMO"]].index)
        else:
            # drop data below altitude
            data_ = data_.drop(data_[data_["Altitude [Pa]"] > alt * 100].index)
        self.file = data_

        return data_

    def o3_rf_from_h2o_emis(self):
        """This function calculates the ozone radiative forcing due to water vapour emission."""

        data_ = self.file.copy()

        rf_o3_30 = [-0.20, -0.20, -0.20, -0.08, -0.08, -0.12, -0.12, -0.12]
        rf_o3_38 = [-0.19, -0.19, -0.19, -0.07, -0.07, -0.09, -0.13, -0.13]

        # use interp and weight functions
        data_ = self.horizontal_interp(
            data_, rf_o3_30, rf_o3_38, "RF / Tg [30 km]", "RF / Tg [38 km]"
        )
        data_ = self.vertical_interp(data_, "RF / Tg")

        # calculate radiative forcing
        data_["O3 RF [mW m-2]"] = self.remove_emission_normalization(
            data_, "H2O [kg]", "RF"
        )
        data_.drop(["RF / Tg"], axis=1, inplace=True)

        # clean and set dtype
        data_ = data_.apply(self.to_numeric, downcast="float", errors="coerce")

        return data_

    def h2o_rf_from_h2o_emis(self):
        """This function calculates the water vapour radiative forcing due to water vapour emission."""

        data_ = self.file.copy()

        rf_h2o_30 = [
            1.70,
            1.70,
            1.70,
            1.90,
            1.90,
            1.65,
            1.34,
            1.34,
        ]
        rf_h2o_38 = [
            1.89,
            1.89,
            1.89,
            1.97,
            1.97,
            1.82,
            1.59,
            1.59,
        ]

        # use interp and weight functions
        data_ = self.horizontal_interp(
            data_, rf_h2o_30, rf_h2o_38, "RF / Tg [30 km]", "RF / Tg [38 km]"
        )
        data_ = self.vertical_interp(data_, "RF / Tg")

        # radiative forcing
        data_["H2O RF [mW m-2]"] = self.remove_emission_normalization(
            data_, "H2O [kg]", "RF"
        )
        data_.drop(["RF / Tg"], axis=1, inplace=True)

        # clean and set dtype
        data_ = data_.apply(self.to_numeric, downcast="float", errors="coerce")

        return data_

    def o3_rf_from_h2_emis(self):
        """This function calculates the ozone radiative forcing due to hydrogen emission."""

        data_ = self.file.copy()

        rf_o3_30 = [-3.04, -3.04, -3.04, -2.46, -2.46, -2.13, -1.75, -1.75]
        rf_o3_38 = [-3.81, -3.81, -3.81, -2.59, -2.59, -2.72, -2.46, -2.46]

        # use interp and weight functions
        data_ = self.horizontal_interp(
            data_, rf_o3_30, rf_o3_38, "RF / Tg [30 km]", "RF / Tg [38 km]"
        )
        data_ = self.vertical_interp(data_, "RF / Tg")

        # calculate radiative forcing
        data_["O3 RF [mW m-2]"] = self.remove_emission_normalization(
            data_, "H2 [kg]", "RF"
        )
        data_.drop(["RF / Tg"], axis=1, inplace=True)

        # clean and set dtype
        data_ = data_.apply(self.to_numeric, downcast="float", errors="coerce")

        return data_

    def h2o_rf_from_h2_emis(self):
        """This function calculates the water vapour radiative forcing due to hydrogen emission."""

        data_ = self.file.copy()

        rf_h2o_30 = [
            5.17,
            5.17,
            5.17,
            7.76,
            7.76,
            2.97,
            1.62,
            1.62,
        ]
        rf_h2o_38 = [
            9.12,
            9.12,
            9.12,
            11.96,
            11.96,
            8.34,
            5.50,
            5.50,
        ]

        # use interp and weight functions
        data_ = self.horizontal_interp(
            data_, rf_h2o_30, rf_h2o_38, "RF / Tg [30 km]", "RF / Tg [38 km]"
        )
        data_ = self.vertical_interp(data_, "RF / Tg")

        # radiative forcing
        data_["H2O RF [mW m-2]"] = self.remove_emission_normalization(
            data_, "H2 [kg]", "RF"
        )
        data_.drop(["RF / Tg"], axis=1, inplace=True)

        # clean and set dtype
        data_ = data_.apply(self.to_numeric, downcast="float", errors="coerce")

        return data_

    def o3_rf_from_no_emis(self):
        """This function calculates the ozone radiative forcing due to nitrogen oxide emission."""

        data_ = self.file.copy()

        rf_o3_30 = [127.0, 127.0, 127.0, 129.9, 129.9, 91.6, 69.9, 69.9]
        rf_o3_38 = [102.9, 102.9, 102.9, 48.2, 48.2, 66.9, 74.3, 74.3]

        # use interp and weight functions
        data_ = self.horizontal_interp(
            data_, rf_o3_30, rf_o3_38, "RF / Tg [30 km]", "RF / Tg [38 km]"
        )
        data_ = self.vertical_interp(data_, "RF / Tg")

        # calculate radiative forcing
        data_["O3 RF [mW m-2]"] = self.remove_emission_normalization(
            data_, "NO [kg]", "RF"
        )
        data_.drop(["RF / Tg"], axis=1, inplace=True)

        # clean and set dtype
        data_ = data_.apply(self.to_numeric, downcast="float", errors="coerce")

        return data_

    def total_rf(self):
        """This function returns the net radiative forcing from ozone (H2O, H2, NO emission) and water vapour (H2O emission)."""

        import pandas as pd

        # calculate radiative forcings for each point of trajectory
        df_h2o = pd.concat(
            [
                self.h2o_rf_from_h2o_emis(),
                self.o3_rf_from_h2o_emis()[["O3 RF [mW m-2]"]],
            ],
            axis=1,
        )
        df_h2 = self.o3_rf_from_h2_emis()
        df_no = self.o3_rf_from_no_emis()

        # Calculate net of all individual radiative forcings
        net = (
            df_h2o["H2O RF [mW m-2]"].sum()
            + df_h2o["O3 RF [mW m-2]"].sum()
            + df_h2["O3 RF [mW m-2]"].sum()
            + df_no["O3 RF [mW m-2]"].sum()
        )

        return net

    def total_o3_rf(self):
        """This function returns the net radiative forcing from ozone (H2O, H2, NO emission)."""

        # calculate radiative forcings for each point of trajectory
        df_h2o = self.o3_rf_from_h2o_emis()
        df_h2 = self.o3_rf_from_h2_emis()
        df_no = self.o3_rf_from_no_emis()

        # Calculate net of all individual o3 radiative forcings
        net = (
            df_h2o["O3 RF [mW m-2]"].sum()
            + df_h2["O3 RF [mW m-2]"].sum()
            + df_no["O3 RF [mW m-2]"].sum()
        )

        return net

    def total_h2o_rf(self):
        """This function returns the net radiative forcing from water vapour (H2O emission)."""

        # calculate radiative forcings for each point of trajectory
        df_h2o = self.h2o_rf_from_h2o_emis()

        # Calculate net of all individual h2o radiative forcings
        net = df_h2o["H2O RF [mW m-2]"].sum()

        return net

    def total_emis(self):
        """This function returns a list of the mass emission in tons (H2O, H2, NO) for the selected altitude."""

        data_ = self.file.copy()

        # Calculate mass emission
        h2o_emis = round(data_["H2O [kg]"].sum() / 1e3, 2)
        h2_emis = round(data_["H2 [kg]"].sum() / 1e3, 2)
        no_emis = round(data_["NO [kg]"].sum() / 1e3, 2)

        return [h2o_emis, h2_emis, no_emis]
