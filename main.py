from fastapi import FastAPI, Body
from fastapi.responses import StreamingResponse
from chatbot import process_input_stream  # Import your chat function

app = FastAPI()

@app.post("/chat")
def chat_endpoint(
    input: str = Body(..., embed=True),
    session_id: str = Body(...),
):
    # Stream output using client-provided session_id
    return StreamingResponse(
        process_input_stream(input, session_id),
        media_type='text/plain'
    )
