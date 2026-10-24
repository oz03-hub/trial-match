from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import mount_frontend


def test_spa_served_and_api_still_routes(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<div id=root></div>")
    (tmp_path / "assets" / "app.js").write_text("console.log(1)")

    app = FastAPI()

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    mount_frontend(app, tmp_path)
    client = TestClient(app)

    assert client.get("/").text == "<div id=root></div>"
    assert client.get("/some/client/route").text == "<div id=root></div>"
    assert client.get("/assets/app.js").text == "console.log(1)"
    assert client.get("/api/health").json() == {"status": "ok"}
    assert client.get("/api/missing").status_code == 404
    assert client.get("/../pyproject.toml").text == "<div id=root></div>"
