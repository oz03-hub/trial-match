"""TrialMatch API. Stateless: the browser resends history + previous lists each turn."""

import logging
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.trials import REPO_ROOT

load_dotenv(REPO_ROOT / ".env")

from app.agent import run_turn  # noqa: E402  (after .env is loaded)
from app.outreach import generate_emails  # noqa: E402
from app.report import build_report  # noqa: E402
from app.schemas import ChatRequest, TrialMatchResponse  # noqa: E402
from app.service import normalize  # noqa: E402
from app.trials import get_store  # noqa: E402

log = logging.getLogger("trialmatch")

ERROR_MESSAGES = {
    "en": "Sorry, something went wrong on my end while searching trials. "
    "Your results so far are kept. Please try sending that again.",
    "es": "Lo siento, algo salió mal al buscar estudios. "
    "Sus resultados se conservan. Intente enviarlo de nuevo.",
    "pt": "Desculpe, algo deu errado ao buscar estudos. "
    "Seus resultados foram mantidos. Tente enviar novamente.",
    "zh": "抱歉，搜索试验时出了点问题。您目前的结果已保留，请再发送一次。",
    "ht": "Padon, gen yon pwoblèm pandan m t ap chèche etid yo. "
    "Rezilta ou yo konsève. Tanpri voye l ankò.",
    "vi": "Xin lỗi, đã xảy ra sự cố khi tìm thử nghiệm. "
    "Kết quả của bạn vẫn được giữ. Vui lòng gửi lại.",
}

app = FastAPI(title="TrialMatch")


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Plain `def`: FastAPI runs it in a threadpool, so the blocking agent is fine.
@app.post("/api/chat")
def chat(request: ChatRequest) -> TrialMatchResponse:
    try:
        response = normalize(run_turn(request), get_store())
    except Exception:
        log.exception("agent turn failed")
        prev = request.previous or TrialMatchResponse(assistant_message="")
        return prev.model_copy(update={
            "assistant_message": ERROR_MESSAGES[request.language],
            "done": False,
            "final_report_markdown": None,
            "error": True,
        })

    if request.finish or response.done:
        response.done = True
        response.next_question = None
        # Never raises: missing/failed emails fall back to a template in build_report.
        emails = generate_emails(request.messages, response)
        response.final_report_markdown = build_report(response, request.language, emails)
    return response



def mount_frontend(app: FastAPI, static_dir: Path) -> None:
    """Serve the built React app from the same origin as the API.

    Unknown non-API paths fall back to index.html (SPA)."""
    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(status_code=404)
        file = (static_dir / path).resolve()
        if file.is_file() and file.is_relative_to(static_dir.resolve()):
            return FileResponse(file)
        return FileResponse(static_dir / "index.html")


STATIC_DIR = REPO_ROOT / "frontend" / "dist"
if STATIC_DIR.is_dir():
    mount_frontend(app, STATIC_DIR)
