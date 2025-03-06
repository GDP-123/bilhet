from io import BytesIO
import pandas as pd


def create_temp_xlsx_file(df, name_file):
    
    excel_file = BytesIO()
    with pd.ExcelWriter(excel_file, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name=name_file)
    excel_file.seek(0)

    return excel_file