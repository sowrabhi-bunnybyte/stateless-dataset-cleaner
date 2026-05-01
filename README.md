Stateless Data Cleaner & Dashboard

An end-to-end **data cleaning and visualization platform** built using FastAPI and React.  
This project combines **automated preprocessing, interactive preview, and dynamic dashboards** to simulate a real-world data preparation tool.

---

Key Features

* Upload datasets (CSV, Excel)

* Automated Data Cleaning
  * Remove duplicates
  * Normalize string values
  * Convert numeric columns
  * Handle missing values (smart fill/drop)
  * Outlier capping using IQR

* Dataset Preview
  * Scrollable table (first 20 rows)
  * Fullscreen preview option

* Interactive Dashboard
  * Pie chart
  * Bar graph
  * Line graph
  * Scatter plot

* Dataset Insights
  * Total rows & columns
  * Numeric vs text columns

* Stateless Processing
  * No data storage
  * Each session is independent

* Download cleaned dataset (CSV)

---

Key Concept

Unlike traditional tools, this system:

> Cleans and transforms data automatically while providing instant visual insights  
> without storing any user data.

This mimics real-world preprocessing pipelines where:

* Clean data → better model performance  
* Structured data → faster analysis  
* Visualization → quicker decision-making  

---

Project Structure

data-cleaner/
│
├── backend/
│ ├── main.py
│ ├── requirements.txt
│
├── frontend/
│ ├── src/
│ │ ├── App.jsx
│ │ ├── Charts.jsx
│ │ ├── DatasetPreview.jsx
│ │ ├── CleaningStats.jsx
│ │ └── assets/
│ ├── package.json
│
└── README.md


---

Tech Stack

**Frontend**
- React
- Vite
- Recharts

**Backend**
- FastAPI
- Python
- Pandas

**Deployment**
- Render (recommended)

---

Installation & Setup

1️⃣ Clone Repository

```
git clone https://github.com/yourusername/data-cleaner.git
cd data-cleaner

cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt

uvicorn main:app --reload
```
Backend runs at:
http://127.0.0.1:8000

```
cd frontend
npm install
npm run dev
```
Frontend runs at:
http://localhost:5173

---

▶️ How to Run

* Upload dataset (CSV/Excel)
* Backend cleans data using Pandas
* Cleaned dataset is returned instantly
  
Frontend:
* Displays preview
* Shows statistics
* Generates charts
* Download cleaned dataset

---

Dashboard Features

* Preview dataset (first 20 rows)
* Expand preview to fullscreen
* Visualize using:
  * Pie chart
  * Bar graph
  * Line graph
  * Scatter plot
View dataset insights instantly

---

Deployment (Render)

Build Command
```
pip install -r backend/requirements.txt && cd frontend && npm install && npm run build
```

Start Command
```
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```
Use Cases

* Data preprocessing for ML
* Exploratory data analysis
* Dataset cleaning automation
* Visualization dashboards
* Academic & portfolio projects

---

Future Improvements

* Support for JSON & Parquet
* Advanced ML-based cleaning
* Column-level profiling
* Real-time collaboration
* Public API endpoints
  
⚠️ Notes
Fully stateless — no data is stored
Works best with structured datasets
Large datasets may take longer to process

---

Author
Sowrabhi Narayanan

⭐ If you like this project, give it a star and feel free to contribute!
