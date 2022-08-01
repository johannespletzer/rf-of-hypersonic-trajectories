"""Python file to read Trajectory .mat files from the folder 'data' and return the radiative forcing as an excel file."""

from glob import glob

from pandas import DataFrame, ExcelWriter

from rf_of_trajectory import rf_of_trajectory


def main():
    """Main code. Loads files and extracts labels, calculates radiative forcing, writes to excel file."""

    files = glob("./Data/*Traj*.mat")
    labels = list(map(lambda a: a.split("ory_")[-1].split("_2022")[0], files))

    # Create lists for each radiative forcing
    tot_rf = []
    h2o_rf = []
    o3_rf = []

    # Calculate radiative forcing for each trajectory 
    for i, file in enumerate(files):
        rf = rf_of_trajectory(file.split()[-1])

        # Load data
        rf.load_trajectory_as_dataframe()

        # Mask values below tropopause
        rf.drop_vertical_levels()  

        tot_rf.append(rf.total_rf())
        h2o_rf.append(rf.total_h2o_rf())
        o3_rf.append(rf.total_o3_rf())

    # Create DataFrame from lists
    df = DataFrame([labels, tot_rf, h2o_rf, o3_rf]).T
    df.columns = ["Trajectory", "RF [mW m-2]", "H2O RF [mW m-2]", "O3 RF [mW m-2]"]
    df.set_index("Trajectory", inplace=True)

    # Write excel file
    writer = ExcelWriter("rf_of_trajectories.xlsx")
    df.to_excel(writer, sheet_name="Radiative Forcing", index=True, na_rep="NaN", engine="xlsxwriter")

    # Adjust column width of excel file
    for column in df:
        column_length = max(df[column].astype(str).map(len).max(), len(column))
        col_idx = df.columns.get_loc(column) + 1
        try:
            writer.sheets["Radiative Forcing"].set_column(col_idx, col_idx, column_length)
        except AttributeError:
            pass 

    writer.save()


if __name__ == "__main__":
    main()
