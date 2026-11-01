# Streamlit Community Cloud notes

Not deployed yet. Settings to use when the app is deployed:

- **Main file:** `streamlit_app.py`
- **Python version:** select **3.12** under *Advanced settings*. The pinned
  `pandas==3.0.5` requires Python 3.11 or newer.
- **Dependencies:** `requirements.txt` (pinned). Test-only packages are in
  `requirements-dev.txt` and are not needed on Cloud.
- **Data:** `B2B_Transaction_Data_.xlsx` (~41 MB) is read from the repository.
  The first load parses the Excel file and is slow; later reruns use
  `st.cache_data`. Measure load time and memory on the real deployment before
  considering a Parquet copy of the data.

Run the tests locally with:

```bash
pip install -r requirements-dev.txt
python -m pytest
```
