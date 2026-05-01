import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ScatterChart,
  Scatter,
  LineChart,
  Line,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
} from "recharts";

export default function Charts({ fullData }) {
  if (!fullData) return null;

  try {
    // Parse the full CSV data
    const lines = fullData.split("\n").filter(Boolean);
    
    // Skip comment lines (those starting with #)
    const dataLines = lines.filter(line => !line.startsWith("#"));
    
    if (dataLines.length < 2) {
      return (
        <div className="charts-section">
          <h2>📊 Dataset Dashboard</h2>
          <p style={{ textAlign: "center", color: "#6b7280", padding: "40px" }}>
            Dataset is empty or invalid. No charts to display.
          </p>
        </div>
      );
    }
    
    const headers = dataLines[0].split(",");
    const rows = dataLines.slice(1).map((line) => line.split(","));

  // ---------- Identify column types ----------
  const numericColumns = [];
  const categoricalColumns = [];

  headers.forEach((header, colIndex) => {
    let numericCount = 0;
    let totalNonEmpty = 0;

    rows.forEach((row) => {
      const val = row[colIndex];
      if (val && val.trim() !== "") {
        totalNonEmpty++;
        if (!isNaN(parseFloat(val))) {
          numericCount++;
        }
      }
    });

    // If more than 80% are numeric, consider it a numeric column
    if (totalNonEmpty > 0 && numericCount / totalNonEmpty > 0.8) {
      numericColumns.push({ name: header, index: colIndex });
    } else {
      categoricalColumns.push({ name: header, index: colIndex });
    }
  });

  // ---------- 1. PIE CHART: Column Type Distribution ----------
  const columnTypeData = [
    { name: "Numeric", value: numericColumns.length, color: "#0088FE" },
    { name: "Categorical", value: categoricalColumns.length, color: "#FFBB28" },
  ];

  // ---------- 2. BAR CHART: Missing Values per Column ----------
  const missingData = headers.map((header, colIndex) => {
    let missingCount = 0;
    rows.forEach((row) => {
      if (!row[colIndex] || row[colIndex].trim() === "") {
        missingCount++;
      }
    });
    return { column: header, missing: missingCount };
  });
  
  // If no missing values at all, show a placeholder
  const hasMissingValues = missingData.some(item => item.missing > 0);
  const missingDataToShow = hasMissingValues 
    ? missingData.filter(item => item.missing > 0)
    : [{ column: "No Missing Values", missing: 0 }];

  // ---------- 3. SCATTER CHART: First two numeric columns ----------
  let scatterData = [];
  let scatterLabels = { x: "X", y: "Y" };
  
  if (numericColumns.length >= 2) {
    const col1 = numericColumns[0];
    const col2 = numericColumns[1];
    scatterLabels = { x: col1.name, y: col2.name };

    scatterData = rows
      .map((row) => {
        const x = parseFloat(row[col1.index]);
        const y = parseFloat(row[col2.index]);
        if (!isNaN(x) && !isNaN(y)) {
          return { x, y };
        }
        return null;
      })
      .filter(Boolean)
      .slice(0, 500); // Limit to 500 points for performance
  }

  // ---------- 4. LINE CHART: Trend of first numeric column ----------
  let lineData = [];
  let lineLabel = "Value";

  if (numericColumns.length >= 1) {
    const col = numericColumns[0];
    lineLabel = col.name;

    lineData = rows
      .map((row, idx) => {
        const val = parseFloat(row[col.index]);
        if (!isNaN(val)) {
          return { index: idx + 1, value: val };
        }
        return null;
      })
      .filter(Boolean)
      .slice(0, 100); // Show first 100 data points
  }

  // ---------- ALTERNATIVE: Distribution chart if we have categorical data ----------
  let distributionData = [];
  let distributionLabel = "Category";

  if (categoricalColumns.length > 0) {
    const col = categoricalColumns[0];
    distributionLabel = col.name;

    const counts = {};
    rows.forEach((row) => {
      const val = row[col.index];
      if (val && val.trim() !== "") {
        counts[val] = (counts[val] || 0) + 1;
      }
    });

    distributionData = Object.entries(counts)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 10); // Top 10 categories
  }

  return (
    <div className="charts-section">
      <h2>Dataset Dashboard</h2>

      <div className="charts-grid">
        {/* 1. PIE CHART - Column Types */}
        <div className="chart-card">
          <h3>Column Type Distribution</h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={columnTypeData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={70}
                label={({ name, value }) => `${name}: ${value}`}
              >
                {columnTypeData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* 2. BAR CHART - Missing Values */}
        <div className="chart-card">
          <h3>Missing Values by Column</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={missingDataToShow}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="column"
                angle={-45}
                textAnchor="end"
                height={80}
                interval={0}
                tick={{ fontSize: 10 }}
              />
              <YAxis />
              <Tooltip />
              <Bar dataKey="missing" fill={hasMissingValues ? "#82ca9d" : "#d1d5db"} />
            </BarChart>
          </ResponsiveContainer>
          {!hasMissingValues && (
            <p style={{ textAlign: "center", color: "#16a34a", fontSize: "12px", marginTop: "8px" }}>
              ✓ No missing values detected
            </p>
          )}
        </div>

        {/* 3. SCATTER CHART - Two numeric columns */}
        <div className="chart-card">
          <h3>
            {numericColumns.length >= 2
              ? `${scatterLabels.x} vs ${scatterLabels.y}`
              : "Scatter Plot"}
          </h3>
          {numericColumns.length >= 2 ? (
            <ResponsiveContainer width="100%" height={250}>
              <ScatterChart>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" dataKey="x" name={scatterLabels.x} />
                <YAxis type="number" dataKey="y" name={scatterLabels.y} />
                <Tooltip cursor={{ strokeDasharray: "3 3" }} />
                <Scatter
                  name="Data Points"
                  data={scatterData}
                  fill="#8884d8"
                />
              </ScatterChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ height: "250px", display: "flex", alignItems: "center", justifyContent: "center", color: "#9ca3af" }}>
              <p style={{ textAlign: "center", padding: "20px" }}>
                Need at least 2 numeric columns<br />for scatter plot
              </p>
            </div>
          )}
        </div>

        {/* 4. LINE CHART - Trend of first numeric column OR Category Distribution */}
        <div className="chart-card">
          <h3>
            {numericColumns.length >= 1
              ? `Trend: ${lineLabel}`
              : distributionData.length > 0
              ? `Top Categories: ${distributionLabel}`
              : "Line Chart"}
          </h3>
          {numericColumns.length >= 1 ? (
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={lineData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="index" label={{ value: "Row Index", position: "insideBottom", offset: -5 }} />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="value" stroke="#FF7300" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : distributionData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={distributionData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="name"
                  angle={-45}
                  textAnchor="end"
                  height={80}
                  interval={0}
                  tick={{ fontSize: 10 }}
                />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#FF7300" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ height: "250px", display: "flex", alignItems: "center", justifyContent: "center", color: "#9ca3af" }}>
              <p style={{ textAlign: "center", padding: "20px" }}>
                No numeric or categorical data<br />available for visualization
              </p>
            </div>
          )}
        </div>
      </div>

      <div className="chart-info">
        <p>
          <strong>Note:</strong> Charts display analysis of the <strong>entire cleaned dataset</strong> ({rows.length.toLocaleString()} rows).
          {scatterData.length > 0 && scatterData.length < rows.length && (
            <> Scatter plot limited to {scatterData.length} points for performance.</>
          )}
        </p>
      </div>
    </div>
  );
  } catch (error) {
    console.error("Error rendering charts:", error);
    return (
      <div className="charts-section">
        <h2>Dataset Dashboard</h2>
        <p style={{ textAlign: "center", color: "#dc2626", padding: "40px" }}>
          Error rendering charts. Please check your dataset format.
        </p>
      </div>
    );
  }
}