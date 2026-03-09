from fastapi import HTTPException


class NaoEncontrado(HTTPException):
    def __init__(self, recurso: str = "Recurso"):
        super().__init__(status_code=404, detail=f"{recurso} não encontrado")


class NaoAutorizado(HTTPException):
    def __init__(self):
        super().__init__(status_code=401, detail="Não autorizado")
