import pytest


@pytest.fixture
def sample_ementa():
    return "Altera a legislação tributária para reduzir alíquota do ICMS sobre produtos da cesta básica"


@pytest.fixture
def sample_deputado_raw():
    return {
        "id": 12345,
        "nome": "João da Silva",
        "nomeCivil": "João Pereira da Silva",
        "siglaPartido": "PT",
        "siglaUf": "SP",
        "urlFoto": "https://example.com/foto.jpg",
        "email": "joao@camara.leg.br",
        "cpf": "12345678901",
        "sexo": "M",
    }
