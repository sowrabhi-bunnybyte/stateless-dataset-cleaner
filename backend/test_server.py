from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"status": "ok"}

@app.post("/test-upload")
async def test_upload(file: UploadFile = File(...)):
    try:
        print(f"Received file: {file.filename}")
        print(f"Content type: {file.content_type}")
        
        # Try to read the file
        content = await file.read()
        print(f"File size: {len(content)} bytes")
        
        # Reset for pandas
        await file.seek(0)
        
        # Try to load with pandas
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file.file)
        elif file.filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file.file)
        else:
            return JSONResponse(status_code=400, content={"error": "Unsupported format"})
        
        print(f"Loaded DataFrame: {df.shape}")
        print(f"Columns: {list(df.columns)}")
        print(f"First row: {df.iloc[0].to_dict() if len(df) > 0 else 'empty'}")
        
        return {
            "success": True,
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": list(df.columns)
        }
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)