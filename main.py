from fastapi import FastAPI
import os

app = FastAPI()

@app.get("/file_list")
def list_files(path: str = "."):

    return [{
        "name": fname,
        "is_file": os.path.isfile(os.path.join(path, fname))
        } for fname in os.listdir(path)]
