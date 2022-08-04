"""Python file to read Trajectory .mat files from the folder 'data'
   and return the radiative forcing as an excel file."""

import sys

from glob import glob

from package import rf_to_excel as rte

from package import rf_of_trajectory as rot


def main():
    """Main code. Loads files and extracts labels, calculates
       radiative forcing, writes to excel file."""

    try:
        filepath = sys.argv[1]
    except IndexError:
        print(
            "\n\tDon't forget to add the filepath \
             like 'python3 main.py <path_to_trajectory_data>'\n"
        )
        sys.exit(1)

    files = glob(filepath + "/*Traj*.mat")
    labels = [a.rsplit("ory_",maxsplit=1)[-1].split("_2022",maxsplit=1)[0] for a in files]

    # Create lists for each radiative forcing
    tot_rf, h2o_rf, o3_rf = [], [], []

    # Calculate radiative forcing for each trajectory
    for file in files:
        trajectory = rot.RadiativeForcingTrajectory(file.split()[-1])

        # Load data
        trajectory.load_trajectory_as_dataframe()

        # Mask values below tropopause
        trajectory.drop_vertical_levels()

        tot_rf.append(trajectory.total_rf())
        h2o_rf.append(trajectory.total_h2o_rf())
        o3_rf.append(trajectory.total_o3_rf())

    # Write results to excel file
    rte.rf_to_excel(labels, tot_rf, h2o_rf, o3_rf)


if __name__ == "__main__":
    main()
