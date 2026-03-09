from app.classification.classifier import classify_proposicao


def test_classify_tributacao(sample_ementa):
    results = classify_proposicao(sample_ementa)
    slugs = [r.slug for r in results]
    assert "tributacao" in slugs


def test_classify_empty():
    results = classify_proposicao("Texto genérico sem relevância")
    assert isinstance(results, list)


def test_classify_multiple_topics():
    ementa = "Dispõe sobre trabalho escravo em áreas de desmatamento na Amazônia"
    results = classify_proposicao(ementa)
    slugs = [r.slug for r in results]
    assert len(slugs) >= 2


def test_classify_saude():
    ementa = "Autoriza o SUS a fornecer medicamentos para tratamento de doenças raras"
    results = classify_proposicao(ementa)
    slugs = [r.slug for r in results]
    assert "saude" in slugs
