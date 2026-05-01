export default function CleaningStats({ stats }) {
  if (!stats) return null;

  const rowsRemoved = (stats.original_rows || 0) - (stats.cleaned_rows || 0);
  const missingFilled = stats.missing_filled || 0;
  const outliersFixed = stats.outliers_capped || 0;
  const duplicatesRemoved = stats.duplicates_removed || 0;
  const numericCols = stats.numeric_columns?.length || 0;
  const categoricalCols = stats.categorical_columns?.length || 0;

  // Check if dataset was already clean
  const wasAlreadyClean = duplicatesRemoved === 0 && missingFilled === 0 && outliersFixed === 0 && rowsRemoved === 0;

  return (
    <div className="stats-section">
      <h2>Cleaning Summary</h2>
      
      {wasAlreadyClean && (
        <div className="already-clean-banner">
          ✓ Dataset was already clean! No cleaning operations needed.
        </div>
      )}
      
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Original Rows</div>
          <div className="stat-value">{(stats.original_rows || 0).toLocaleString()}</div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Cleaned Rows</div>
          <div className="stat-value">{(stats.cleaned_rows || 0).toLocaleString()}</div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Duplicates Removed</div>
          <div className={`stat-value ${duplicatesRemoved > 0 ? 'highlight-red' : ''}`}>
            {duplicatesRemoved.toLocaleString()}
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Missing Values Filled</div>
          <div className={`stat-value ${missingFilled > 0 ? 'highlight-green' : ''}`}>
            {missingFilled.toLocaleString()}
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Outliers Capped</div>
          <div className={`stat-value ${outliersFixed > 0 ? 'highlight-orange' : ''}`}>
            {outliersFixed.toLocaleString()}
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Total Rows Removed</div>
          <div className={`stat-value ${rowsRemoved > 0 ? 'highlight-red' : ''}`}>
            {rowsRemoved.toLocaleString()}
          </div>
        </div>
      </div>

      <div className="operations-summary">
        <h3>Operations Performed:</h3>
        <ul>
          <li>Normalized column names (lowercase, underscores)</li>
          {duplicatesRemoved > 0 && <li>Removed {duplicatesRemoved.toLocaleString()} duplicate rows</li>}
          {missingFilled > 0 && <li>Filled {missingFilled.toLocaleString()} missing values (median for numeric, mode for categorical)</li>}
          {(stats.columns_converted_to_numeric?.length || 0) > 0 && (
            <li>Converted {stats.columns_converted_to_numeric.length} columns to numeric format</li>
          )}
          {outliersFixed > 0 && <li>Capped {outliersFixed.toLocaleString()} outlier values using IQR method (1.5 × IQR)</li>}
          {(stats.rows_dropped_empty || 0) > 0 && <li>Dropped {stats.rows_dropped_empty} mostly-empty rows</li>}
          <li>Cleaned text fields (trimmed whitespace, standardized formatting)</li>
        </ul>
        
        <div className="column-breakdown">
          <p><strong>Final Column Breakdown:</strong></p>
          <p>Numeric: {numericCols} columns</p>
          <p>Categorical: {categoricalCols} columns</p>
        </div>
      </div>
    </div>
  );
}