def rf_to_excel(labels, tot_rf, h2o_rf, o3_rf):
    """Function to export the calculated radiative forcings to an excel file"""

    from pandas import DataFrame, ExcelWriter

    # Create DataFrame from lists
    df = DataFrame([labels, tot_rf, h2o_rf, o3_rf]).T
    df.columns = ["Trajectory", "RF [mW m-2]", "H2O RF [mW m-2]", "O3 RF [mW m-2]"]
    df.set_index("Trajectory", inplace=True)

    # Write excel file
    writer = ExcelWriter("rf_of_trajectories.xlsx")
    df.to_excel(
        writer,
        sheet_name="Radiative Forcing",
        index=True,
        na_rep="NaN",
        engine="xlsxwriter",
    )

    # Adjust column width of excel file
    for column in df:
        column_length = max(df[column].astype(str).map(len).max(), len(column))
        col_idx = df.columns.get_loc(column) + 1
        try:
            writer.sheets["Radiative Forcing"].set_column(
                col_idx, col_idx, column_length
            )
        except AttributeError:
            pass

    writer.save()
