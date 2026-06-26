from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.analyzer import analyze_ticket_rule_based
from src.llm import maybe_enhance_with_gemini
from src.models import TicketRequest, TicketResponse

app = FastAPI(title="QueueStorm Investigator API", version="1.0.0")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={"error": "Malformed or schema-invalid input. Please check required fields and enum values."},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal error while analyzing ticket."},
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/analyze-ticket", response_model=TicketResponse)
async def analyze_ticket(request: TicketRequest):
    if not request.complaint or not request.complaint.strip():
        raise HTTPException(status_code=422, detail="Complaint cannot be empty")

    base_response = analyze_ticket_rule_based(request)
    final_response = await maybe_enhance_with_gemini(
        base_response=base_response,
        complaint=request.complaint,
        language=request.language,
    )
    return final_response
