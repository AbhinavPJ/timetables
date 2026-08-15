# Karnataka PUC Timetable Generator

## Windows setup

1. Install Python 3.11 or later from [python.org](https://www.python.org/downloads/). During installation, select **Add Python to PATH**.
2. Open PowerShell in this project folder and run:

   ```powershell
   py -m venv venv
   .\venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   streamlit run app.py
   ```

3. Open the displayed local URL in your browser. Upload or edit the dashboard JSON, then download the generated CSV or Excel report.

## macOS setup

1. Install Python 3.11 or later from [python.org](https://www.python.org/downloads/), then open Terminal in this project folder.
2. Run:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   python -m pip install -r requirements.txt
   streamlit run app.py
   ```

3. Open the displayed local URL in your browser. Upload or edit the dashboard JSON, then download the generated CSV or Excel report.
