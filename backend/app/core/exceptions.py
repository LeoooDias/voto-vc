from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class NaoEncontrado(HTTPException):
    def __init__(self, recurso: str = "Recurso"):
        super().__init__(status_code=404, detail=f"{recurso} não encontrado")


class NaoAutorizado(HTTPException):
    def __init__(self):
        super().__init__(status_code=401, detail="Não autorizado")


class ErroValidacao(HTTPException):
    def __init__(self, detail: str = "Dados inválidos"):
        super().__init__(status_code=422, detail=detail)


class ErroInterno(HTTPException):
    def __init__(self):
        super().__init__(status_code=500, detail="Erro interno do servidor")


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "erro": exc.detail,
            "status": exc.status_code,
            "request_id": request_id,
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=500,
        content={
            "erro": "Erro interno do servidor",
            "status": 500,
            "request_id": request_id,
        },
    )
