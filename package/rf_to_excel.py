"""Function to export lists of radiative forcings to excel file."""

from pandas import DataFrame, ExcelWriter


def rf_to_excel(labels, tot_rf, h2o_rf, o3_rf):
    """Function to export the radiative forcings to an excel file"""

    # Create DataFrame from lists
    data_frame = DataFrame([labels, tot_rf, h2o_rf, o3_rf]).T
    data_frame.columns = [
        "Trajectory",
        "RF [mW m-2]",
        "H2O RF [mW m-2]",
        "O3 RF [mW m-2]",
    ]
    data_frame.set_index("Trajectory", inplace=True)

    # Write excel file
    writer = ExcelWriter("rf_of_trajectories.xlsx")
    data_frame.to_excel(
        writer,
        sheet_name="Radiative Forcing",
        index=True,
        na_rep="NaN",
        engine="xlsxwriter",
    )

    # Adjust column width of excel file
    for column in data_frame:
        column_length = max(data_frame[column].astype(str).map(len).max(), len(column))
        col_idx = data_frame.columns.get_loc(column) + 1
        try:
            writer.sheets["Radiative Forcing"].set_column(
                col_idx, col_idx, column_length
            )
        except AttributeError:
            pass

    writer.save()
