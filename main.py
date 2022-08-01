"""Python file to read Trajectory .mat files from the folder 'data' and return the radiative forcing as an excel file."""

from glob import glob

from pandas import DataFrame, ExcelWriter

from rf_to_excel import rf_to_excel

from rf_of_trajectory import rf_of_trajectory


def main():
    """Main code. Loads files and extracts labels, calculates radiative forcing, writes to excel file."""

    files = glob("./Data/*Traj*.mat")
    labels = [a.split("ory_")[-1].split("_2022")[0] for a in files]

    # Create lists for each radiative forcing
    tot_rf = []
    h2o_rf = []
    o3_rf = []

    # Calculate radiative forcing for each trajectory
    for file in files:
        rf = rf_of_trajectory(file.split()[-1])

        # Load data
        rf.load_trajectory_as_dataframe()

        # Mask values below tropopause
        rf.drop_vertical_levels()

        tot_rf.append(rf.total_rf())
        h2o_rf.append(rf.total_h2o_rf())
        o3_rf.append(rf.total_o3_rf())

    # Write results to excel file
    rf_to_excel(labels, tot_rf, h2o_rf, o3_rf)


if __name__ == "__main__":
    main()
