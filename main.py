from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse

BASE_DIR = Path("/data")
UPLOADS_DIR = BASE_DIR / "uploads"
RESULTS_DIR = BASE_DIR / "results"

TEXT_TO_ADD = "\n\n--- Added by FastAPI server ---\n"
LINE_TO_ADD = "This line was added by the FastAPI server.\n"

app = FastAPI(title="File Processor API")


def ensure_dirs() -> None:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def process_file(input_path: Path) -> Path:
    content = input_path.read_text(encoding="utf-8")
    modified_content = content + TEXT_TO_ADD

    output_path = RESULTS_DIR / input_path.name
    output_path.write_text(modified_content, encoding="utf-8")

    with output_path.open(mode="a", encoding="utf-8") as f:
        for row in input_path.read_text(encoding="utf-8").splitlines():
            f.write(row + LINE_TO_ADD)

    return output_path


@app.on_event("startup")
def startup() -> None:
    ensure_dirs()


@app.get("/")
def root():
    return {"message": "File Processor API is running"}


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    ensure_dirs()

    if not file.filename:
        raise HTTPException(status_code=400, detail="File must have a name")

    if not file.filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt files are supported")

    file_path = UPLOADS_DIR / file.filename

    content = await file.read()
    file_path.write_bytes(content)

    return {
        "status": "uploaded",
        "filename": file.filename,
        "saved_to": str(file_path),
    }


@app.post("/process/{filename}")
def process_uploaded_file(filename: str):
    ensure_dirs()

    input_path = UPLOADS_DIR / filename
    if not input_path.exists():
        raise HTTPException(status_code=404, detail="Uploaded file not found")

    output_path = process_file(input_path)

    return {
        "status": "processed",
        "input_file": filename,
        "output_file": output_path.name,
        "download_url": f"/download/{output_path.name}",
    }


@app.post("/process-all")
def process_all_files():
    ensure_dirs()

    input_files = list(UPLOADS_DIR.glob("*.txt"))
    if not input_files:
        return {
            "status": "success",
            "processed_files": [],
            "count": 0,
            "message": "No uploaded .txt files found",
        }

    processed_files = []
    for input_file in input_files:
        output_path = process_file(input_file)
        processed_files.append(output_path.name)

    return {
        "status": "success",
        "processed_files": processed_files,
        "count": len(processed_files),
    }


@app.get("/files/uploads")
def list_uploaded_files():
    ensure_dirs()
    files = [f.name for f in UPLOADS_DIR.glob("*") if f.is_file()]
    return {"uploaded_files": files}


@app.get("/files/results")
def list_result_files():
    ensure_dirs()
    files = [f.name for f in RESULTS_DIR.glob("*") if f.is_file()]
    return {"result_files": files}


@app.get("/download/{filename}")
def download_result_file(filename: str):
    file_path = RESULTS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Processed file not found")

    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type="text/plain",
    )