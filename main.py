from fastapi import FastAPI

app = FastAPI()


@app.get("/greet")
def handle_test(name: str = "test_name"):
    return {
            "text": f"Hello {name}"
            }

