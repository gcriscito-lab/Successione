import uvicorn
from successioni.web import crea_app
uvicorn.run(crea_app(token="t0k", porta=8812), host="127.0.0.1", port=8812, log_level="warning")
