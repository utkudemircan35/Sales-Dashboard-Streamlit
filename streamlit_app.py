import pandas as pd
import streamlit as st

st.set_page_config(layout="wide")


def prepare_data(file_name):
    data = pd.read_excel(file_name)

    # Remove rows that are identical in every column
    data = data.drop_duplicates()

    # Calculate SalesAmount for each row
    data["SalesAmount"] = data["Quantity"] * data["NetPrice"]

    return data

def reset_filters():
    st.session_state["selected_codes"] = []
    st.session_state["selected_dates"] = []
    st.session_state["selected_descriptions"] = []
    st.session_state["selected_categories"] = []
    st.session_state["selected_cities"] = []
    st.session_state["filters_applied"] = False


data = prepare_data("B2B_Transaction_Data_.xlsx")

if "filters_applied" not in st.session_state:
    st.session_state["filters_applied"] = False

st.title("B2B Transaction Data")
st.subheader("Filters")

dates = sorted(data["InvoiceDate"].dropna().astype(str).unique())

categories = sorted(data["Category"].dropna().astype(str).unique())
cities = sorted(data["City"].dropna().astype(str).unique())

with st.form("filters"):
    col1, col2, col3= st.columns(3)
    with col1:
        st.multiselect("Invoice Date", dates, key="selected_dates")
    with col2:
        st.multiselect("Category", categories, key="selected_categories")
    with col3:
        st.multiselect("City", cities, key="selected_cities")

    apply_filters = st.form_submit_button("Apply Filters")

st.button("Reset Filters", on_click=reset_filters)

if apply_filters:
    st.session_state["filters_applied"] = True

filtered_data = data

# Apply filters to the data based on user selections
if st.session_state["filters_applied"]:

    if st.session_state["selected_dates"]:
        filtered_data = filtered_data[
            filtered_data["InvoiceDate"].astype(str).isin(
                st.session_state["selected_dates"]
            )
        ]

    if st.session_state["selected_categories"]:
        filtered_data = filtered_data[
            filtered_data["Category"].astype(str).isin(
                st.session_state["selected_categories"]
            )
        ]

    if st.session_state["selected_cities"]:
        filtered_data = filtered_data[
            filtered_data["City"].isin(st.session_state["selected_cities"])
        ]

st.dataframe(filtered_data, use_container_width=True)