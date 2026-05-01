from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import io
import re
import numpy as np

app = FastAPI(title="Data Cleaner – Production Final")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    print("=" * 50)
    print("Server starting up...")
    print(f"Pandas version: {pd.__version__}")
    print("All imports successful")
    print("=" * 50)


@app.get("/")
async def root():
    return {"status": "ok", "message": "Dataset Cleaner API is running"}


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "pandas_version": pd.__version__,
        "endpoints": ["/clean", "/clean/preview", "/clean/stats"]
    }


# ---------- ENHANCED NUMERIC CLEANER ----------
def clean_numeric(series: pd.Series, preserve_text=False):
    """
    Enhanced numeric cleaning with text preservation option
    """
    if preserve_text:
        sample = series.dropna().astype(str).head(100)
        avg_length = sample.str.len().mean()
        has_spaces = sample.str.contains(' ').sum() / len(sample) if len(sample) > 0 else 0
        
        if avg_length > 50 or has_spaces > 0.7:
            return series  # Don't convert text to numeric
    
    cleaned = (
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace(r"[$₹€£¥]", "", regex=True)
        .str.replace("lbs", "", regex=False)
        .str.replace("kg", "", regex=False)
        .str.replace("cm", "", regex=False)
        .str.strip()
    )
    
    # Handle M (millions) and K (thousands) separately
    multiplier = pd.Series(1, index=cleaned.index)
    
    has_m = cleaned.str.contains('M', case=False, regex=False)
    multiplier.loc[has_m] = 1_000_000
    cleaned = cleaned.str.replace('M', '', case=False, regex=False)
    
    has_k = cleaned.str.contains('K', case=False, regex=False)
    multiplier.loc[has_k & ~has_m] = 1_000
    cleaned = cleaned.str.replace('K', '', case=False, regex=False)
    
    cleaned = cleaned.str.replace(r"\(.*?\)", "", regex=True).str.strip()
    
    numbers = cleaned.str.extract(r"([-+]?\d*\.?\d+)")[0]
    numeric_result = pd.to_numeric(numbers, errors="coerce") * multiplier
    
    return numeric_result


# ---------- DETECT COLUMN PURPOSE ----------
def detect_column_type(series: pd.Series, col_name: str):
    """Detect column type to determine cleaning strategy"""
    col_lower = col_name.lower()
    
    # URL detection
    if 'url' in col_lower or 'link' in col_lower:
        return 'url'
    
    # ID detection
    if col_lower in ['id', 'player_id', 'user_id', 'transaction_id'] or col_lower.endswith('_id'):
        return 'id'
    
    # Date detection
    if 'date' in col_lower or 'joined' in col_lower or 'created' in col_lower:
        return 'date'
    
    # Long text detection
    if 'description' in col_lower or 'review' in col_lower or 'comment' in col_lower or 'summary' in col_lower:
        return 'text'
    
    sample = series.dropna().astype(str).head(100)
    
    if len(sample) == 0:
        return 'unknown'
    
    # URL by content
    if sample.str.contains('http://|https://|www\.', case=False, regex=True).sum() > len(sample) * 0.5:
        return 'url'
    
    # Long text by length
    avg_length = sample.str.len().mean()
    if avg_length > 100:
        return 'text'
    
    # Numeric check
    numeric_test = pd.to_numeric(sample.str.replace(',', ''), errors='coerce')
    if numeric_test.notna().sum() > len(sample) * 0.8:
        return 'numeric'
    
    # Categorical check
    unique_ratio = len(sample.unique()) / len(sample)
    if unique_ratio < 0.1:
        return 'categorical'
    
    return 'unknown'


# ---------- SALARY RANGE EXTRACTOR (ENHANCED) ----------
def extract_salary_ranges(df: pd.DataFrame):
    """
    Enhanced salary extractor that handles:
    - $137K-$171K (Glassdoor est.)
    - $50,000-$75,000
    - Removes estimation text
    """
    salary_cols = [col for col in df.columns if 'salary' in col.lower() or 'pay' in col.lower() or 'wage' in col.lower()]
    
    for col in salary_cols:
        if df[col].dtype == 'object':
            sample = df[col].dropna().astype(str).head(100)
            
            # Check if it contains ranges
            if sample.str.contains(r'\d+[KkMm]?\s*-\s*\d+[KkMm]?').any():
                print(f"✓ Extracting salary range from: {col}")
                
                # Remove estimation text first
                cleaned_salary = (
                    df[col]
                    .astype(str)
                    .str.replace(r'\(.*?est\.*\)', '', regex=True, flags=re.IGNORECASE)
                    .str.replace(r'\(.*?\)', '', regex=True)
                    .str.strip()
                )
                
                # Extract min and max
                min_vals = cleaned_salary.str.extract(r'([\d.]+)[KkMm]?\s*-')[0]
                max_vals = cleaned_salary.str.extract(r'-\s*([\d.]+)[KkMm]?')[0]
                
                # Detect multiplier (K or M)
                if sample.str.contains('K', case=False).sum() > len(sample) * 0.5:
                    multiplier = 1000
                elif sample.str.contains('M', case=False).sum() > len(sample) * 0.5:
                    multiplier = 1_000_000
                else:
                    multiplier = 1
                
                df[f'{col}_min'] = pd.to_numeric(min_vals, errors='coerce') * multiplier
                df[f'{col}_max'] = pd.to_numeric(max_vals, errors='coerce') * multiplier
                df[f'{col}_avg'] = (df[f'{col}_min'] + df[f'{col}_max']) / 2
                
                # Drop original messy column
                df = df.drop(columns=[col])
                print(f"  Created: {col}_min, {col}_max, {col}_avg")
    
    return df


# ---------- REVENUE EXTRACTOR ----------
def extract_revenue(df: pd.DataFrame):
    """
    Extract revenue from messy formats like:
    - $1 to $2 billion (USD)
    - $500 million to $1 billion
    - Unknown / $500 million to $1 billion (USD)
    """
    revenue_cols = [col for col in df.columns if 'revenue' in col.lower() or 'gross' in col.lower()]
    
    for col in revenue_cols:
        if df[col].dtype == 'object':
            sample = df[col].dropna().astype(str).head(100)
            
            # Check if it contains text like "billion" or "million"
            if sample.str.contains('billion|million', case=False, regex=True).sum() > len(sample) * 0.3:
                print(f"✓ Extracting revenue from: {col}")
                
                # Clean the text
                cleaned = df[col].astype(str)
                
                # Extract min and max values
                min_vals = cleaned.str.extract(r'([\d.]+)\s*(?:to|-)')[0]
                max_vals = cleaned.str.extract(r'(?:to|-)\s*([\d.]+)')[0]
                
                # If no range, just extract single value
                single_vals = cleaned.str.extract(r'([\d.]+)\s*(?:billion|million)')[0]
                
                # Determine multiplier
                is_billion = cleaned.str.contains('billion', case=False)
                is_million = cleaned.str.contains('million', case=False)
                
                # Create numeric columns
                df[f'{col}_min_numeric'] = pd.to_numeric(min_vals, errors='coerce')
                df[f'{col}_max_numeric'] = pd.to_numeric(max_vals, errors='coerce')
                
                # If no range found, use single value
                df[f'{col}_min_numeric'] = df[f'{col}_min_numeric'].fillna(pd.to_numeric(single_vals, errors='coerce'))
                df[f'{col}_max_numeric'] = df[f'{col}_max_numeric'].fillna(pd.to_numeric(single_vals, errors='coerce'))
                
                # Apply multiplier
                df.loc[is_billion, f'{col}_min_numeric'] *= 1_000_000_000
                df.loc[is_billion, f'{col}_max_numeric'] *= 1_000_000_000
                df.loc[is_million, f'{col}_min_numeric'] *= 1_000_000
                df.loc[is_million, f'{col}_max_numeric'] *= 1_000_000
                
                # Calculate average
                df[f'{col}_avg'] = (df[f'{col}_min_numeric'] + df[f'{col}_max_numeric']) / 2
                
                # Keep original for reference
                print(f"  Created: {col}_min_numeric, {col}_max_numeric, {col}_avg")
    
    return df


# ---------- COMPANY NAME CLEANER ----------
def clean_company_names(df: pd.DataFrame):
    """Remove ratings from company names"""
    company_cols = [col for col in df.columns if 'company' in col.lower() or 'employer' in col.lower()]
    
    for col in company_cols:
        if df[col].dtype == 'object':
            df[col] = (
                df[col].astype(str)
                .str.replace(r'\n.*', '', regex=True)
                .str.replace(r'\d+\.\d+$', '', regex=True)
                .str.strip()
            )
            print(f"✓ Cleaned company names in: {col}")
    
    return df


# ---------- LOCATION SPLITTER ----------
def split_location(df: pd.DataFrame):
    """Split location into city/state"""
    location_cols = [col for col in df.columns if 'location' in col.lower()]
    
    for col in location_cols:
        if df[col].dtype == 'object':
            sample = df[col].dropna().astype(str).head(100)
            if sample.str.contains(',').sum() > len(sample) * 0.5:
                print(f"✓ Splitting location: {col}")
                
                split_data = df[col].str.split(',', n=1, expand=True)
                df[f'{col}_city'] = split_data[0].str.strip() if 0 in split_data.columns else None
                df[f'{col}_state'] = split_data[1].str.strip() if 1 in split_data.columns else None
                
                df = df.drop(columns=[col])
    
    return df


# ---------- DIRECTOR/STARS SPLITTER ----------
def split_director_stars(df: pd.DataFrame):
    """Split director and stars from combined columns"""
    text_cols = [col for col in df.columns if 'star' in col.lower() or 'director' in col.lower()]
    
    for col in text_cols:
        if df[col].dtype == 'object':
            sample = df[col].dropna().astype(str).head(10)
            
            if sample.str.contains('Director:', case=False).any() and sample.str.contains('Stars:', case=False).any():
                print(f"✓ Splitting director and stars from: {col}")
                
                df['director'] = df[col].str.extract(r'Director:\s*([^\n|]+)', flags=re.IGNORECASE)[0]
                df['director'] = df['director'].str.strip()
                
                df['stars'] = df[col].str.extract(r'Stars:\s*([^\n]+)', flags=re.IGNORECASE)[0]
                df['stars'] = df['stars'].str.strip()
                
                df = df.drop(columns=[col])
    
    return df


# ---------- REPLACE -1 PLACEHOLDERS ----------
def replace_placeholder_values(df: pd.DataFrame):
    """Replace placeholders with NaN, but don't replace valid -1 values"""
    placeholders = ['Unknown', 'unknown', 'N/A', 'n/a', 'NA', 
                   'Not sure', 'not sure', 'Personal', 'personal', '?']
    
    for col in df.columns:
        # Replace text placeholders
        df[col] = df[col].replace(placeholders, np.nan)
        
        # For numeric columns, only replace -1 if it's clearly a placeholder
        # (appears frequently and doesn't make sense in context)
        if pd.api.types.is_numeric_dtype(df[col]):
            col_lower = col.lower()
            # Only replace -1 if:
            # 1. It appears in >5% of values AND
            # 2. The column is not something where -1 could be meaningful (like temperature, profit/loss)
            if (df[col] == -1).sum() > len(df) * 0.05:
                # Don't replace -1 in financial columns where it could mean loss
                if not any(word in col_lower for word in ['profit', 'change', 'delta', 'diff']):
                    df[col] = df[col].replace(-1, np.nan)
                    print(f"✓ Replaced -1 placeholders in: {col}")
    
    return df


# ---------- CLEAN FOOTNOTES ----------
def clean_footnotes(df: pd.DataFrame):
    """Remove Wikipedia-style footnote references"""
    for col in df.select_dtypes(include='object').columns:
        sample = df[col].dropna().astype(str).head(100)
        if sample.str.contains(r'\[\d+\]').sum() > len(sample) * 0.3:
            print(f"✓ Removing footnotes from: {col}")
            df[col] = df[col].astype(str).str.replace(r'\[\d+\]', '', regex=True).str.strip()
    
    return df


# ---------- YEAR EXTRACTION ----------
def extract_year(series: pd.Series):
    """Extract 4-digit year from messy formats"""
    if series.dtype == 'object':
        years = series.astype(str).str.extract(r"(\d{4})")[0]
        return pd.to_numeric(years, errors="coerce")
    return series


# ---------- SMART OUTLIER DETECTION ----------
def should_cap_outliers(col_name: str, series: pd.Series):
    """
    Determine if outliers should be capped
    
    CRITICAL: For most real-world data, outliers are MEANINGFUL, not errors!
    Only cap outliers for physical/scientific measurements where values outside
    a range are impossible or indicate data entry errors.
    """
    col_lower = col_name.lower()
    
    # NEVER cap these - outliers are the whole point!
    never_cap_keywords = [
        'vote', 'view', 'like', 'follower', 'subscriber', 'hit',  # Popularity
        'gross', 'revenue', 'sales', 'earning', 'income',  # Financial success
        'rating', 'score', 'rank', 'ova', 'overall', 'potential', 'pot',  # Quality/ability
        'wage', 'salary', 'price', 'value', 'worth',  # Market values
        'attendance', 'ticket', 'box_office',  # Event metrics
        'founded', 'year', 'date',  # Historical data
        'gpa', 'grade',  # Academic performance
    ]
    
    if any(keyword in col_lower for keyword in never_cap_keywords):
        return False
    
    # ONLY cap these - physical impossibilities
    # Even then, use extreme caution!
    maybe_cap_keywords = [
        'age',  # Only if someone entered 999
        'height',  # Only if someone entered 9999 cm
        'weight',  # Only if someone entered 9999 kg
    ]
    
    if any(keyword in col_lower for keyword in maybe_cap_keywords):
        # Even for these, only cap if there are truly impossible values
        # For height: >300cm is impossible
        # For weight: >600kg is extremely rare
        # For age: >120 is impossible
        if 'height' in col_lower:
            return series.max() > 300  # Only cap if there's a >300cm value
        if 'weight' in col_lower:
            return series.max() > 600  # Only cap if there's a >600kg value
        if 'age' in col_lower:
            return series.max() > 120  # Only cap if there's a >120 age
    
    # Default: DON'T cap outliers
    return False


# ---------- CORE CLEANING PIPELINE ----------
def run_cleaning_pipeline(df: pd.DataFrame):
    try:
        if df is None or df.empty:
            raise ValueError("DataFrame is empty or None")
        
        print(f"\n{'='*60}")
        print(f"STARTING CLEANING PIPELINE")
        print(f"{'='*60}")
        print(f"Initial shape: {len(df)} rows × {len(df.columns)} columns")
        
        original_rows = len(df)
        original_cols = len(df.columns)
        original_missing = int(df.isnull().sum().sum())
        
        # ========== COLUMN NAME CLEANING ==========
        print(f"\n{'='*60}")
        print("STEP 1: COLUMN NAME STANDARDIZATION")
        print(f"{'='*60}")
        
        try:
            df.columns = df.columns.astype(str)
            df.columns = (
                df.columns
                .str.strip()
                .str.lower()
                .str.replace(" ", "_", regex=False)
                .str.replace(r"[^\w_]", "", regex=True)
            )
            print(f"✓ Standardized {len(df.columns)} column names")
        except Exception as e:
            print(f"✗ Error cleaning column names: {e}")
            df.columns = [f"col_{i}" for i in range(len(df.columns))]

        # ========== DETECT COLUMN TYPES ==========
        print(f"\n{'='*60}")
        print("STEP 2: COLUMN TYPE DETECTION")
        print(f"{'='*60}")
        
        column_types = {}
        for col in df.columns:
            col_type = detect_column_type(df[col], col)
            column_types[col] = col_type
            if col_type in ['text', 'url', 'id']:
                print(f"{col:35} → {col_type:15} [PROTECTED]")

        # ========== DATASET-SPECIFIC CLEANING ==========
        print(f"\n{'='*60}")
        print("STEP 3: SMART DATA EXTRACTION")
        print(f"{'='*60}")
        
        df = clean_company_names(df)
        df = extract_salary_ranges(df)  # Enhanced version
        df = extract_revenue(df)  # New!
        df = split_location(df)
        df = split_director_stars(df)
        df = clean_footnotes(df)
        df = replace_placeholder_values(df)
        
        # Extract years
        year_cols = [col for col in df.columns if 'year' in col.lower()]
        for col in year_cols:
            if df[col].dtype == 'object':
                original_year = df[col].iloc[0] if len(df) > 0 else None
                df[col] = extract_year(df[col])
                print(f"✓ Extracted year from: {col} (e.g., '{original_year}' → {df[col].iloc[0]})")

        # ========== REMOVE DUPLICATES ==========
        print(f"\n{'='*60}")
        print("STEP 4: DUPLICATE REMOVAL")
        print(f"{'='*60}")
        
        original_duplicates = int(df.duplicated().sum())
        
        if original_duplicates > 0:
            normalized_df = df.copy()
            try:
                for col in normalized_df.select_dtypes(include="object"):
                    if column_types.get(col) not in ['url', 'id']:
                        normalized_df[col] = (
                            normalized_df[col]
                            .astype(str)
                            .str.lower()
                            .str.strip()
                            .str.replace(r"\s+", " ", regex=True)
                        )
            except Exception as e:
                print(f"⚠ Warning normalizing for dedup: {e}")

            df = df.loc[~normalized_df.duplicated()]
            print(f"✓ Removed {original_duplicates} duplicates ({len(df)} rows remaining)")
        else:
            print(f"✓ No duplicates found")

        # ========== STRING CLEANUP ==========
        print(f"\n{'='*60}")
        print("STEP 5: TEXT CLEANING")
        print(f"{'='*60}")
        
        try:
            for col in df.select_dtypes(include="object"):
                if column_types.get(col) not in ['url', 'text', 'id']:
                    df[col] = (
                        df[col]
                        .astype(str)
                        .str.strip()
                        .str.replace(r"\s+", " ", regex=True)
                        .str.replace('\n', ' ', regex=False)
                        .replace("nan", "")
                        .replace("None", "")
                    )
            print(f"✓ Cleaned whitespace and formatting")
        except Exception as e:
            print(f"⚠ Warning cleaning strings: {e}")

        # ========== SMART NUMERIC CONVERSION ==========
        print(f"\n{'='*60}")
        print("STEP 6: NUMERIC CONVERSION")
        print(f"{'='*60}")
        
        numeric_cols_before = df.select_dtypes(include="number").columns.tolist()
        cols_converted_to_numeric = []
        
        for col in df.columns:
            if df[col].dtype == 'object' and column_types.get(col) not in ['url', 'text', 'id', 'date']:
                numeric_candidate = clean_numeric(df[col], preserve_text=True)
                
                conversion_rate = numeric_candidate.notna().sum() / len(df)
                if conversion_rate > 0.6:
                    sample_original = df[col].iloc[0] if len(df) > 0 else None
                    df[col] = numeric_candidate
                    cols_converted_to_numeric.append(col)
                    print(f"✓ {col:35} (e.g., '{sample_original}' → {df[col].iloc[0]})")

        if len(cols_converted_to_numeric) == 0:
            print("✓ No additional columns converted (already numeric or should stay text)")

        # ========== DROP MOSTLY EMPTY ROWS ==========
        print(f"\n{'='*60}")
        print("STEP 7: EMPTY ROW REMOVAL")
        print(f"{'='*60}")
        
        rows_before_empty_drop = len(df)
        df = df.dropna(thresh=int(len(df.columns) * 0.4))
        rows_dropped_empty = rows_before_empty_drop - len(df)
        
        if rows_dropped_empty > 0:
            print(f"✓ Dropped {rows_dropped_empty} mostly-empty rows")
        else:
            print(f"✓ No empty rows to remove")

        # ========== MISSING VALUE HANDLING ==========
        print(f"\n{'='*60}")
        print("STEP 8: MISSING VALUE IMPUTATION")
        print(f"{'='*60}")
        
        missing_before_fill = int(df.isnull().sum().sum())
        
        if missing_before_fill > 0:
            print(f"Found {missing_before_fill} missing values")
            print(f"⚠ IMPORTANT: Missing values will be filled with median/mode")
            print(f"  This creates 'artificial' data - use with caution!")
            
            for col in df.columns:
                if df[col].isnull().any():
                    missing_count = df[col].isnull().sum()
                    if pd.api.types.is_numeric_dtype(df[col]):
                        fill_value = df[col].median()
                        df[col] = df[col].fillna(fill_value)
                        print(f"  • {col}: Filled {missing_count} with median ({fill_value:.2f})")
                    elif column_types.get(col) not in ['url', 'text']:
                        mode = df[col].mode()
                        fill_value = mode[0] if not mode.empty else "Unknown"
                        df[col] = df[col].fillna(fill_value)
                        print(f"  • {col}: Filled {missing_count} with mode ('{fill_value}')")
        else:
            print(f"✓ No missing values to fill")

        # ========== SMART OUTLIER CAPPING ==========
        print(f"\n{'='*60}")
        print("STEP 9: OUTLIER ANALYSIS")
        print(f"{'='*60}")
        print(f"⚠ CRITICAL: Most outliers are MEANINGFUL, not errors!")
        print(f"  Only capping truly impossible values...")
        
        outliers_capped = 0
        capped_columns = []
        
        for col in df.select_dtypes(include="number"):
            if should_cap_outliers(col, df[col]):
                q1 = df[col].quantile(0.25)
                q3 = df[col].quantile(0.75)
                iqr = q3 - q1
                if iqr > 0:
                    lower_bound = q1 - 1.5 * iqr
                    upper_bound = q3 + 1.5 * iqr
                    outliers_in_col = ((df[col] < lower_bound) | (df[col] > upper_bound)).sum()
                    if outliers_in_col > 0:
                        outliers_capped += outliers_in_col
                        capped_columns.append(col)
                        df[col] = df[col].clip(lower_bound, upper_bound)
                        print(f"  ✓ {col}: Capped {outliers_in_col} impossible values")
        
        if outliers_capped == 0:
            print(f"✓ No outliers capped (all data preserved)")
        else:
            print(f"\n⚠ Total outliers capped: {outliers_capped} across {len(capped_columns)} columns")

        # ========== FINAL STATS ==========
        stats = {
            "original_rows": original_rows,
            "cleaned_rows": len(df),
            "original_columns": original_cols,
            "final_columns": len(df.columns),
            "duplicates_removed": original_duplicates,
            "rows_dropped_empty": rows_dropped_empty,
            "original_missing": original_missing,
            "missing_filled": missing_before_fill,
            "remaining_missing": int(df.isnull().sum().sum()),
            "outliers_capped": int(outliers_capped),
            "numeric_columns": df.select_dtypes(include="number").columns.tolist(),
            "categorical_columns": df.select_dtypes(include="object").columns.tolist(),
            "columns_converted_to_numeric": cols_converted_to_numeric,
        }
        
        print(f"\n{'='*60}")
        print(f"CLEANING COMPLETE ✓")
        print(f"{'='*60}")
        print(f"Final shape: {len(df)} rows × {len(df.columns)} columns")
        print(f"Data quality: {((len(df) * len(df.columns) - stats['remaining_missing']) / (len(df) * len(df.columns)) * 100):.1f}% complete")

        return df, stats
        
    except Exception as e:
        print(f"\n✗ ERROR in cleaning pipeline: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


# ---------- FILE LOADER ----------
def load_dataframe(file: UploadFile):
    try:
        file.file.seek(0)
        
        filename = file.filename.lower()
        if filename.endswith(".csv"):
            try:
                return pd.read_csv(file.file, encoding='utf-8')
            except (pd.errors.ParserError, UnicodeDecodeError) as e:
                print(f"⚠ CSV parsing error: {e}")
                print("Attempting recovery with lenient settings...")
                
                file.file.seek(0)
                content = file.file.read()
                if isinstance(content, bytes):
                    for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
                        try:
                            text_content = content.decode(encoding)
                            break
                        except:
                            continue
                    else:
                        text_content = content.decode('utf-8', errors='ignore')
                else:
                    text_content = content
                
                from io import StringIO
                
                try:
                    csv_io = StringIO(text_content)
                    return pd.read_csv(
                        csv_io,
                        on_bad_lines='warn',
                        engine='python',
                        skipinitialspace=True,
                        encoding_errors='ignore'
                    )
                except:
                    csv_io = StringIO(text_content)
                    return pd.read_csv(
                        csv_io,
                        on_bad_lines='skip',
                        engine='python',
                        skipinitialspace=True
                    )
                    
        elif filename.endswith((".xlsx", ".xls")):
            return pd.read_excel(file.file)
        else:
            return None
            
    except Exception as e:
        print(f"✗ Error loading file: {e}")
        import traceback
        traceback.print_exc()
        raise


# ---------- ENDPOINTS ----------
@app.post("/clean")
async def clean_dataset(file: UploadFile = File(...)):
    try:
        print(f"\n{'#'*60}")
        print(f"# NEW CLEANING REQUEST: {file.filename}")
        print(f"{'#'*60}")
        
        df = load_dataframe(file)
        if df is None:
            return JSONResponse(status_code=400, content={"error": "Unsupported file format"})

        cleaned_df, stats = run_cleaning_pipeline(df)

        output = io.StringIO()
        output.write(f"# Original rows: {stats['original_rows']}\n")
        output.write(f"# Cleaned rows: {stats['cleaned_rows']}\n")
        output.write(f"# Duplicates removed: {stats['duplicates_removed']}\n")
        output.write(f"# Missing values filled: {stats['missing_filled']}\n")
        output.write(f"# Outliers capped: {stats['outliers_capped']}\n")
        output.write(f"# WARNING: Filled values are ESTIMATES, not real data\n")

        cleaned_df.to_csv(output, index=False)
        output.seek(0)

        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=cleaned_data.csv"
            },
        )

    except Exception as e:
        print(f"✗ Error in /clean endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/clean/preview")
async def clean_preview(file: UploadFile = File(...), limit: int = 50):
    try:
        df = load_dataframe(file)
        if df is None:
            return JSONResponse(status_code=400, content={"error": "Unsupported file format"})

        cleaned_df, stats = run_cleaning_pipeline(df)

        return {
            "columns": cleaned_df.columns.tolist(),
            "preview": cleaned_df.head(limit).to_dict(orient="records"),
            "stats": stats
        }

    except Exception as e:
        print(f"✗ Error in /clean/preview: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/clean/stats")
async def clean_stats(file: UploadFile = File(...)):
    try:
        df = load_dataframe(file)
        if df is None:
            return JSONResponse(status_code=400, content={"error": "Unsupported file format"})

        _, stats = run_cleaning_pipeline(df)
        
        return stats

    except Exception as e:
        print(f"✗ Error in /clean/stats: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

    
frontend_path = "../frontend/dist"
app.mount("/static", StaticFiles(directory=f"{frontend_path}/assets"), name="static")

@app.get("/")
def serve_frontend():
    index_file = os.path.join(frontend_path, "index.html")
    return FileResponse(index_file)