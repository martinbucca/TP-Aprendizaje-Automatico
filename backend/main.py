from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from vector_rag import find_chunk

app = FastAPI()

# Habilita CORS para todas las rutas
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Puedes especificar dominios permitidos aquí en vez de "*"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelo de datos para la solicitud
class QueryRequest(BaseModel):
    query: str

# Endpoint para recibir queries del frontend
@app.post("/find_chunk")
async def find_chunk_endpoint(request: QueryRequest):
    query = request.query
    if query:
        answer = find_chunk(query)
        return {"answer": answer}
    else:
        raise HTTPException(status_code=400, detail="No se ingresó una consulta válida.")

# Solo es necesario si quieres correr el servidor directamente con Python, aunque normalmente usarías uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5000, log_level="info")
