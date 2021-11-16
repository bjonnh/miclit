import streamlit as st
import itrmicfit.engine as imf_engine
import itrmicfit.plotting as imf_plotting
from matplotlib.figure import Figure
import tempfile

st.set_page_config(layout="wide")
st.header("ITR MIC Fit")
st.write("""
You can upload an XLS(x) file from the plate reader. And it will calculate the MICs for you.

It accepts two formats for the files. Please take a look at the example files.
The plate reader format allows for one plate at a time, the combined format allows you to have
as many entries as you want.
""")
with st.expander("Click here for more help"):
    with open("data/basic_example.xlsx", "rb") as file:
        st.download_button("Basic plate-reader example", data=file, file_name="basic_example.xlsx")

    with open("data/multirow_example.xlsx", "rb") as file:
        st.download_button("Multirow RAW example", data=file, file_name="multirow_example.xlsx")

    st.header("Plate reader format")
    st.write("""
    Requirements:
     - Data starts in B16 and ends in M23
     - Columns B and M are blanks and L is bacterial control
     - Column N contain the names of the compound (if you put the same name on two rows, data will be combined)
     - Column O contains the initial concentration    
    """)

    st.header("RAW format")
    st.write("""
    Requirements:
     - Sheet name must be: **RAW** (in uppercase)
     - Data starts in A1 and ends in column M and can be arbitrary long.
     - Columns A and L are blanks and K is bacterial control
     - Column M contain the names of the compound (if you put the same name on two rows, data will be combined)
     - Column N contains the initial concentration    
    """)

uploaded_file = st.file_uploader("Choose a XLS file formatted properly for this software")

mic_value = st.number_input("MIC percentage to fit", value=90, min_value=1, max_value=99)

if uploaded_file is not None:
    engine = imf_engine.Engine()
    engine.load_file(uploaded_file)
    engine.MICn = mic_value
    engine.fit()
    with st.expander("Source data"):
        st.dataframe(engine.data.data)

    figure = Figure(figsize=(20, 20), tight_layout=True)
    imf_plotting.plot(engine.fits, figure)
    st.pyplot(figure)

    st.header("Tables")

    st.dataframe(engine.export_as_dataframe())

    graphics = st.checkbox("Export graphics", value=True)
    temp_file = tempfile.NamedTemporaryFile()
    out = engine.export_as_spreadsheet(temp_file.name, graphics=graphics, fits=engine.fits)
    st.download_button("Export table", data=temp_file.read(), file_name="export.xlsx")
    temp_file.delete = True
    temp_file.close()
