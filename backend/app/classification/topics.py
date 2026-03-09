"""Canonical topic definitions for classifying legislative propositions."""

from dataclasses import dataclass


@dataclass
class TopicDef:
    slug: str
    nome: str
    descricao: str
    icone: str
    cor: str


TOPICS = [
    TopicDef("economia", "Economia", "Politica economica, fiscal e monetaria", "💰", "#2563EB"),
    TopicDef("tributacao", "Tributacao", "Impostos, taxas e reforma tributaria", "🏛️", "#7C3AED"),
    TopicDef("saude", "Saude", "Sistema de saude, SUS, medicamentos", "🏥", "#DC2626"),
    TopicDef("educacao", "Educacao", "Ensino basico, superior, pesquisa", "📚", "#EA580C"),
    TopicDef("meio-ambiente", "Meio Ambiente", "Desmatamento, clima, fauna, flora, saneamento", "🌿", "#16A34A"),
    TopicDef("seguranca", "Seguranca Publica", "Policia, armas, sistema penal, violencia", "🛡️", "#475569"),
    TopicDef("direitos-humanos", "Direitos Humanos", "Direitos civis, minorias, igualdade", "⚖️", "#DB2777"),
    TopicDef("trabalho", "Trabalho", "Direitos trabalhistas, emprego, previdencia", "👷", "#CA8A04"),
    TopicDef("agricultura", "Agricultura", "Agronegocio, reforma agraria, alimentos", "🌾", "#65A30D"),
    TopicDef("defesa", "Defesa Nacional", "Forcas armadas, fronteiras, soberania", "🎖️", "#0F766E"),
    TopicDef("tecnologia", "Tecnologia", "Internet, dados pessoais, inovacao, IA", "💻", "#6366F1"),
    TopicDef("corrupcao", "Corrupcao e Transparencia", "Combate a corrupcao, transparencia publica", "🔍", "#B91C1C"),
    TopicDef("previdencia", "Previdencia", "Aposentadoria, INSS, reforma previdenciaria", "👴", "#78716C"),
    TopicDef("habitacao", "Habitacao", "Moradia, programas habitacionais, aluguel", "🏠", "#0891B2"),
    TopicDef("transporte", "Transporte", "Infraestrutura, mobilidade urbana, rodovias", "🚌", "#F59E0B"),
    TopicDef("cultura", "Cultura", "Artes, patrimonio cultural, esporte", "🎭", "#A855F7"),
]
