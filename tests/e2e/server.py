import uvicorn
from successioni.web import crea_app
uvicorn.run(crea_app(token="t0k", porta=8813), host="127.0.0.1", port=8813, log_level="warning")
