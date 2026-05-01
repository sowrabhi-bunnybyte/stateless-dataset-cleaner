import { useState } from "react";
import DatasetPreview from "./DatasetPreview";
import Charts from "./Charts";
import CleaningStats from "./CleaningStats";
import logo from "./assets/logo.png";


function parseCSV(text) {
  try {
    const lines = text.split("\n").filter(line => line.trim() !== "" && !line.startsWith("#"));
    
    if (lines.length === 0) {
      throw new Error("CSV is empty");
    }
    
    const headers = lines[0].split(",").map(h => h.trim());
    const rows = lines.slice(1).map((line) => {
      const cells = line.split(",").map(cell => cell.trim());
      // Pad with empty strings if row is shorter than headers
      while (cells.length < headers.length) {
        cells.push("");
      }
      return cells;
    });
    
    return { headers, rows };
  } catch (error) {
    console.error("Error parsing CSV:", error);
    return { headers: [], rows: [] };
  }
}

export default function App() {
  const [file, setFile] = useState(null);
  const [fullData, setFullData] = useState(null); // full cleaned CSV
  const [preview, setPreview] = useState(null);   // first 20 rows for preview
  const [stats, setStats] = useState(null);       // cleaning statistics
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const submit = async () => {
    if (!file) return;

    setLoading(true);
    setError(null);
    setFullData(null);
    setPreview(null);
    setStats(null);

    const form = new FormData();
    form.append("file", file);

    try {
      // Get the full cleaned dataset
      const cleanRes = await fetch("http://127.0.0.1:8000/clean", {
        method: "POST",
        body: form,
      });

      if (!cleanRes.ok) {
        throw new Error(`Server error: ${cleanRes.status}`);
      }

      const text = await cleanRes.text();
      
      console.log("Received data length:", text.length);
      console.log("First 200 chars:", text.substring(0, 200));
      
      if (!text || text.trim() === "") {
        throw new Error("Received empty response from server");
      }
      
      setFullData(text);

      // Parse for preview (first 20 rows)
      const parsed = parseCSV(text);
      
      console.log("Parsed headers:", parsed.headers);
      console.log("Parsed rows count:", parsed.rows.length);
      
      if (!parsed.headers || parsed.headers.length === 0) {
        throw new Error("Invalid CSV format: no headers found");
      }
      
      setPreview({ headers: parsed.headers, rows: parsed.rows.slice(0, 20) });

      // Get cleaning statistics
      const statsForm = new FormData();
      statsForm.append("file", file);
      
      const statsRes = await fetch("http://127.0.0.1:8000/clean/stats", {
        method: "POST",
        body: statsForm,
      });

      if (!statsRes.ok) {
        console.warn("Failed to fetch stats, continuing without them");
      } else {
        const statsData = await statsRes.json();
        console.log("Stats received:", statsData);
        setStats(statsData);
      }

    } catch (err) {
      console.error("Error cleaning dataset:", err);
      setError(err.message || "Failed to clean dataset");
    } finally {
      setLoading(false);
    }
  };

  const download = () => {
    if (!fullData) return;
    const blob = new Blob([fullData], { type: "text/csv" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "cleaned_data.csv";
    a.click();
  };

  return (
    <div className="container">
      {/* ---------- APP HEADER WITH LOGO ---------- */}
      <div className="app-header">
      <img src={logo} alt="Logo" className="app-logo" />
      <h1>Dataset Cleaner</h1>
    </div>

      <input type="file" onChange={(e) => setFile(e.target.files[0])} />
      <button disabled={!file || loading} onClick={submit}>
        {loading ? "Cleaning..." : "Clean Dataset"}
      </button>

      {error && (
        <div className="error-message">
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Preview Table */}
      {preview && (
        <DatasetPreview
          preview={preview}
          showModal={showModal}
          setShowModal={setShowModal}
          download={download}
        />
      )}

      {/* Cleaning Statistics */}
      {stats && <CleaningStats stats={stats} />}

      {/* Charts Dashboard - using full dataset */}
      {fullData && <Charts fullData={fullData} />}
    </div>
  );
}