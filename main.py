"""Python file to read emission inventory files from the folder
   and return the radiative forcing in an excel file."""

import sys

from glob import glob

from package import to_excel as rte

from package import calculate_rf as rot


def main():
    """Main code. Loads files and extracts labels, calculates
       radiative forcing, writes to excel file."""

    try:
        filepath = sys.argv[1]
    except IndexError:
        print(
            "\n\tDon't forget to add the filepath \
             like 'python3 main.py <path_to_emission_inventory_data>'\n"
        )
        sys.exit(1)

    files = glob(filepath + "/*.nc")+glob(filepath + "/*.mat")
    file_names = [a.split('/')[-1] for a in files]

    # Create lists for each radiative forcing
    tot_rf, h2o_rf, o3_rf = [], [], []

    # Calculate radiative forcing for each emission_inventory
    for file in files:
        emission_inventory = rot.EmissionInventory(file.split()[-1])

        # Mask values below tropopause
        emission_inventory.drop_vertical_levels()

        tot_rf.append(emission_inventory.total_rf())
        h2o_rf.append(emission_inventory.total_h2o_rf())
        o3_rf.append(emission_inventory.total_o3_rf())

    # Write results to excel file
    rte.to_excel(file_names, tot_rf, h2o_rf, o3_rf)


if __name__ == "__main__":
    main()
