# Single-Server Queue Simulator (Streamlit)

Small Streamlit app that simulates a single-server queue. Configure number of customers, optional random seed, or provide custom random-number (RN) lists for inter-arrival times (IAT) and service times (ST).

## Requirements
- Python 3.8+
- Windows (PowerShell)
- Packages: streamlit, pandas, altair

## Quick start (PowerShell)
1. Open project folder:
   ```
   cd "e:\Simulation Lab"
   ```

2. Create & activate virtual environment:
   ```
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies:
   ```
   pip install --upgrade pip
   pip install streamlit pandas altair
   ```

4. Run the app:
   ```
   streamlit run app_design.py
   ```
   (If your file is named `app.py` use that name instead.)

## Usage notes
- Number of customers: integer ≥ 1.
- Random seed: optional; passed to Python's random.seed(...) for reproducible runs.
- Custom RN lists: enable the toggle and paste comma/newline separated integers.
  - RN for IAT must be in 1..1000.
  - RN for ST must be in 1..100.
  - Both lists must have length equal to the number of customers.

## Output
- KPIs: average wait, max wait, total idle, utilization, horizon end.
- Charts: wait-by-customer, TSE timeline, wait histogram.
- Results table and CSV download buttons (results & summaries).

## Troubleshooting
- If Streamlit reports unknown widget `st.toggle`, upgrade Streamlit:
  ```
  pip install --upgrade streamlit
  ```
  or replace `st.toggle` with `st.checkbox` in the code.
- To run on a different port:
  ```
  streamlit run app_design.py --server.port 8502
  ```
```<!-- filepath: e:\Simulation Lab\README.md -->

# Single-Server Queue Simulator (Streamlit)

Small Streamlit app that simulates a single-server queue. Configure number of customers, optional random seed, or provide custom random-number (RN) lists for inter-arrival times (IAT) and service times (ST).

## Requirements
- Python 3.8+
- Windows (PowerShell)
- Packages: streamlit, pandas, altair

## Quick start (PowerShell)
1. Open project folder:
   ```
   cd "e:\Simulation Lab"
   ```

2. Create & activate virtual environment:
   ```
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies:
   ```
   pip install --upgrade pip
   pip install streamlit pandas altair
   ```

4. Run the app:
   ```
   streamlit run app_design.py
   ```
   (If your file is named `app.py` use that name instead.)

## Usage notes
- Number of customers: integer ≥ 1.
- Random seed: optional; passed to Python's random.seed(...) for reproducible runs.
- Custom RN lists: enable the toggle and paste comma/newline separated integers.
  - RN for IAT must be in 1..1000.
  - RN for ST must be in 1..100.
  - Both lists must have length equal to the number of customers.

## Output
- KPIs: average wait, max wait, total idle, utilization, horizon end.
- Charts: wait-by-customer, TSE timeline, wait histogram.
- Results table and CSV download buttons (results & summaries).

## Troubleshooting
- If Streamlit reports unknown widget `st.toggle`, upgrade Streamlit:
  ```
  pip install --upgrade streamlit
  ```
  or replace `st.toggle` with `st.checkbox` in the code.
- To run on a different port:
  ```
  streamlit run app_design.py --server.port 8502
  ```