# Algoritmo de Matching — Documentação Técnica

> Arquivo principal: `backend/app/services/matching.py`
> Endpoint: `POST /api/matching/calcular`
> Router: `backend/app/routers/matching.py`

---

## Índice

1. [Visão geral](#visão-geral)
2. [Inputs do usuário](#inputs-do-usuário)
3. [Matching de parlamentar](#matching-de-parlamentar)
4. [Matching de partido](#matching-de-partido)
5. [Confidence dampening (Bayesiano)](#confidence-dampening-bayesiano)
6. [Posições e expansão](#posições-e-expansão)
7. [Casos especiais e edge cases](#casos-especiais-e-edge-cases)
8. [Fórmulas resumidas](#fórmulas-resumidas)
9. [Fluxo completo passo a passo](#fluxo-completo-passo-a-passo)

---

## Visão geral

O sistema compara as respostas do usuário a proposições legislativas com os votos reais de parlamentares no Congresso (Câmara e Senado). O resultado é um score de 0 a 100 para cada parlamentar e partido, onde:

- **100** = concordância total (votou igual ao usuário em tudo)
- **50** = neutro / sem tendência clara
- **0** = discordância total (votou oposto ao usuário em tudo)

Cada resultado inclui um indicador de **confiança** (`"alta"`, `"media"`, `"baixa"`) e, para parlamentares, um ratio de **presença** (proporção de proposições em que o parlamentar votou).

---

## Inputs do usuário

### Slider de 5 posições

O frontend oferece um slider com 5 posições que mapeiam para `(voto, peso)`:

| Posição | Label         | `voto` | `peso` |
|---------|---------------|--------|--------|
| 1       | Contra        | `nao`  | 1.00   |
| 2       | Contra leve   | `nao`  | 0.50   |
| 3       | Neutro        | `sim`  | 0.00   |
| 4       | A favor leve  | `sim`  | 0.50   |
| 5       | A favor       | `sim`  | 1.00   |

> **Neutro** é armazenado como `voto=sim, peso=0.0`. No matching, Neutro é tratado como **"pular"** — a proposição é completamente ignorada no cálculo (não conta para `props_compared`, `concordou`, nem `min_compared`).

Além das 5 posições, o usuário pode **Pular** a proposição (`voto=pular`), com o mesmo efeito de exclusão.

### Estrutura da resposta

```python
class RespostaItem:
    proposicao_id: int
    voto: VotoUsuario  # "sim" | "nao" | "pular"
    peso: float        # 0.0 a 1.0
```

---

## Matching de parlamentar

### Função: `_score_parlamentar()`

Para cada proposição onde **ambos** (usuário e parlamentar) têm posição:

#### 1. Filtrar respostas efetivas do usuário

- Se `voto == "pular"` ou `peso == 0` (Neutro): proposição ignorada completamente.
- Apenas votos com `peso > 0` são "opinionated" e entram no cálculo.

#### 2. Filtrar votos elegíveis do parlamentar

O parlamentar pode ter vários votos registrados por proposição (uma proposição pode ter múltiplas votações). O sistema pega o **primeiro voto SIM ou NAO** encontrado, ignorando:

- `ABSTENCAO`
- `AUSENTE`
- `OBSTRUCAO`
- `PRESENTE_SEM_VOTO`

**Se o parlamentar não tem nenhum voto SIM/NAO para a proposição, ela é ignorada no cálculo.**

#### 3. Calcular concordância/discordância

Para cada proposição comparável (peso > 0, ambos votaram):

```
Se usuário e parlamentar concordam (ambos SIM ou ambos NAO):
    total_score += peso
    concordou += 1

Se discordam:
    total_score -= peso

props_compared += 1
total_weight += peso
```

#### 4. Normalizar para 0-100

```python
normalized = ((total_score / total_weight) + 1) * 50
```

| `total_score / total_weight` | Score |
|-----------------------------|-------|
| +1.0 (concordância total)   | 100   |
| 0.0 (empate)                | 50    |
| -1.0 (discordância total)   | 0     |

#### 5. Mínimo de comparações

O parlamentar só aparece nos resultados se:

```python
props_compared >= min_compared
min_compared = _min_compared(n_opinionated)  # max(3, n_opinionated // 4)
```

Onde `n_opinionated` = respostas com `voto in ("sim", "nao")` **e** `peso > 0`. Neutro e Pular não contam.

#### 6. Presença

Cada parlamentar retorna um campo `presenca` indicando em que proporção das proposições do usuário ele votou:

```python
presenca = votos_comparados / n_opinionated
```

### Ranking: Confidence Score (Bayesiano)

O ranking final **não** usa o score raw. Usa um score ajustado por confiança:

```python
_CONFIDENCE_K = 5

confidence_score = (raw_score * n_compared + 50 * K) / (n_compared + K)
```

Isso puxa scores com poucas comparações em direção a 50 (prior neutro). Exemplos:

| Score raw | Comparações | Confidence score |
|-----------|-------------|------------------|
| 90        | 3           | 65.0             |
| 90        | 10          | 76.7             |
| 90        | 20          | 82.0             |
| 90        | 50          | 86.4             |
| 70        | 3           | 57.5             |
| 70        | 20          | 66.0             |

**O confidence score é usado tanto para ordenação quanto para a exibição visual.** O frontend exibe o score como 5 dots (cada um pode estar vazio, meio ou cheio), convertendo o confidence score para uma escala de 0-10 em incrementos de 0.5. O raw score não é exibido diretamente ao usuário.

---

## Matching de partido

### Abordagem híbrida: Orientação + Voto Majoritário

O partido é calculado de forma diferente do parlamentar. Usa-se uma abordagem híbrida com duas fontes:

#### Fonte 1 (prioritária): Orientação de bancada

A orientação é a instrução oficial do partido/bancada sobre como votar. Valores possíveis:

| Orientação  | Comportamento no matching |
|-------------|--------------------------|
| `SIM`       | Partido votou SIM        |
| `NAO`       | Partido votou NAO        |
| `LIBERADO`  | **Proposição ignorada** (pulada) |
| `ABSTENCAO` | **Ignorada** (cai para fallback) |
| `OBSTRUCAO` | **Ignorada** (cai para fallback) |

A resolução de orientação segue esta prioridade:
1. Orientação direta pela sigla do partido (ex: `PT`)
2. Orientação via bloco parlamentar do qual o partido faz parte (ex: `Bloco PT/PCdoB`)

#### Fonte 2 (fallback): Voto majoritário com margem mínima

Se não há orientação SIM/NAO disponível, o sistema calcula o **voto majoritário** dos parlamentares do partido:

- Conta votos SIM e NAO dos membros do partido naquela proposição
- Calcula `ratio = max(sim, nao) / total`
- Se `ratio < 60%` → **proposição ignorada** (partido dividido demais)
- Se SIM é maioria → partido votou "sim"
- Se NAO é maioria → partido votou "nao"

O **peso efetivo** de votos vindos de majoritário é ponderado pela unanimidade:

```python
effective_peso = peso * vote_strength  # vote_strength = majority_count / total
```

Isso faz com que um partido que votou 95% SIM contribua com peso quase integral, enquanto um que votou 65% SIM contribua com peso reduzido.

Para votos vindos de **orientação**, o peso é integral (sem ponderação).

#### Condição de exibição

O partido só aparece com score se pelo menos um de seus parlamentares atingiu o `min_compared` (verificado via `_score_parlamentar`). Se nenhum parlamentar do partido atingiu o threshold, o partido aparece com `score: null`.

#### Exclusões

- Partidos com sigla `"S/Partido"` são excluídos.

#### Ordenação de partidos

Partidos são ordenados por **confidence score** (mesma fórmula Bayesiana dos parlamentares, usando `votos_comparados` como n). Partidos com score `null` vão para o final.

---

## Confidence dampening (Bayesiano)

### Fórmula

```
adjusted = (raw * n + 50 * K) / (n + K)
```

Onde `K = 5` (constante fixa).

### Intuição

É uma média ponderada entre o score observado e um prior neutro (50). Com poucas observações, o prior domina. Com muitas, o score observado domina.

### Onde é usado

- **Parlamentar ranking**: Ordena por confidence score (n = votos_comparados).
- **Parlamentar display**: Confidence score → 5 dots.
- **Partido ranking**: Ordena por confidence score (n = votos_comparados).
- **Partido display**: Confidence score → 5 dots.
- **Comparação individual** (`comparar_parlamentar`, `comparar_partido`): Confidence score → 5 dots.

### Indicador de confiança

Cada resultado inclui um campo `confianca` derivado do número de comparações efetivas:

| Comparações | Confiança |
|-------------|-----------|
| >= 8        | `"alta"`  |
| >= 4        | `"media"` |
| < 4         | `"baixa"` |

---

## Posições e expansão

### O que são posições

Posições são agrupamentos temáticos (ex: "A favor da reforma tributária") que contêm múltiplas proposições, cada uma com uma `direcao` (`sim` ou `nao`) indicando se votar SIM naquela proposição é estar a favor ou contra a posição.

### Como entram no matching

O endpoint `/api/matching/calcular` aceita dois tipos de respostas:

1. `respostas`: votos diretos em proposições (ex: do questionário)
2. `posicao_respostas`: votos em posições (ex: da tela de posições)

#### Expansão de posições

Quando há `posicao_respostas`, o sistema as **expande** em respostas por proposição:

```python
expandir_posicoes_para_respostas(posicao_respostas, posicoes_map, overrides)
```

A expansão inverte o voto se a `direcao` for contrária:

| Voto do usuário na posição | Direção da proposição | Voto expandido na proposição |
|---------------------------|----------------------|------------------------------|
| `sim` (a favor da posição) | `sim` | `sim` |
| `sim` (a favor da posição) | `nao` | `nao` |
| `nao` (contra a posição)   | `sim` | `nao` |
| `nao` (contra a posição)   | `nao` | `sim` |

#### Overrides de proposição individual

Se o usuário votou **diretamente** em uma proposição (via questionário) **e** essa proposição também faz parte de uma posição, **o voto direto prevalece**.

#### Diluição de peso nas posições

O peso é **diluído** pela quantidade de proposições da posição:

```python
peso_por_prop = peso / len(props)
```

Se o usuário votou "A favor" (peso=1.0) em uma posição com 5 proposições, cada uma entra com peso=0.2. Isso garante que uma posição com muitas proposições não domine o score em relação a votos individuais do questionário.

---

## Casos especiais e edge cases

### Voto Neutro (peso = 0)

O Neutro é `voto=sim, peso=0.0`. No matching, é tratado identicamente a "pular":

- Não conta para `props_compared`
- Não conta para `concordou` ou `discordou`
- Não conta para `n_opinionated` (e portanto não afeta `min_compared`)
- A proposição é completamente excluída do cálculo

### Parlamentar ausente / abstenção / obstrução

Votos do tipo `ABSTENCAO`, `AUSENTE`, `OBSTRUCAO`, `PRESENTE_SEM_VOTO` são **completamente ignorados**. O parlamentar é tratado como se não tivesse votado naquela proposição.

**Não há penalidade direta por ausência**, mas o campo `presenca` permite ao frontend exibir essa informação ao usuário. Um parlamentar com 10% de presença pode ter score alto, mas o usuário verá claramente que ele votou em poucas proposições.

### Múltiplas votações por proposição

Uma proposição pode ter mais de uma votação (destaques, emendas, etc.). O sistema pega **todos os votos do parlamentar** em todas as votações daquela proposição e usa o **primeiro SIM ou NAO** encontrado (ordenado por `votacao_id DESC`, ou seja, a votação mais recente primeiro).

### Partido: orientação LIBERADO

Quando a orientação do partido é `LIBERADO`, a proposição é **ignorada** no cálculo. Não contribui para concordância nem discordância.

### Partido: orientação ABSTENCAO / OBSTRUCAO

Essas orientações **não** são mapeadas para SIM/NAO. O sistema cai para o **fallback de voto majoritário**. Isso é diferente de LIBERADO (que pula completamente).

### Partido: margem insuficiente no voto majoritário

Se a maioria não atinge 60% (ex: 55% SIM vs 45% NAO), a proposição é **ignorada**. Isso previne que partidos muito divididos apareçam com posição clara.

### Empate no ranking de parlamentares

O desempate usa:
1. Confidence score (maior primeiro)
2. Raw score (maior primeiro)
3. `parlamentar_id` (menor primeiro — determinístico)

### Zero `total_weight`

Se o total_weight for 0 (ex: todas as respostas são Neutro com peso 0), o score é `None` (não calculável).

### Nenhuma resposta

Se `respostas` está vazio, retorna `{"parlamentares": [], "partidos": []}`.

---

## Fórmulas resumidas

### Score bruto (parlamentar e partido)

```
score = ((Σ score_i / Σ peso_i) + 1) × 50
```

Onde para cada proposição comparável (peso > 0):
- Concordância: `score_i = +peso`
- Discordância: `score_i = -peso`

Para partidos com voto majoritário como fonte, o peso efetivo é `peso × unanimidade_ratio`.

### Confidence score (ranking de parlamentar e partido)

```
adjusted = (score × n + 50 × 5) / (n + 5)
```

### Min comparações

```
n_opinionated = count(voto in (sim, nao) AND peso > 0)
min_compared = max(3, floor(n_opinionated / 4))
```

### Confiança

```
confianca = "alta"  if effective_compared >= 8
          = "media" if effective_compared >= 4
          = "baixa" otherwise
```

### Presença (parlamentar)

```
presenca = votos_comparados / n_opinionated
```

---

## Fluxo completo passo a passo

### 1. Request chega em `POST /api/matching/calcular`

```json
{
  "respostas": [
    {"proposicao_id": 10, "voto": "sim", "peso": 1.0},
    {"proposicao_id": 20, "voto": "nao", "peso": 0.5}
  ],
  "posicao_respostas": [
    {"posicao_id": 1, "voto": "sim", "peso": 1.0}
  ],
  "uf": "SP",
  "casa": null,
  "limit": 50
}
```

### 2. Resolução de respostas

- Se user logado e sem respostas no body → busca do DB
- Se há `posicao_respostas` → expande via `expandir_posicoes_para_respostas()` (com diluição de peso)
- Respostas diretas (do questionário) prevalecem sobre expandidas de posições

### 3. Carga de dados

- Filtra proposições efetivas (`voto != "pular"` e `peso > 0`)
- Carrega IDs de parlamentares (filtrados por UF/casa se fornecidos)
- Carrega **todos os votos** dos parlamentares elegíveis nas proposições filtradas (uma única query)
- Calcula `min_compared = _min_compared(n_opinionated)`

### 4. Scoring de parlamentares

Para cada parlamentar com votos:
- Executa `_score_parlamentar()` com todas as proposições (Neutro e Pular já filtrados)
- Descarta se `props_compared < min_compared`
- Ordena por `confidence_score` (Bayesiano)
- Retorna top N com raw score, presença e confiança

### 5. Scoring de partidos

- Carrega orientações de bancada para todas as votações
- Carrega mapeamento partido → blocos
- Para cada partido:
  - Verifica se tem pelo menos 1 parlamentar que atingiu `min_compared`
  - Executa `_score_partido_hybrid()`:
    - Para cada proposição: tenta orientação → fallback para voto majoritário (com margem mínima de 60%)
    - Peso ponderado pela unanimidade quando fonte é voto majoritário
    - Calcula score com mesma fórmula
- Ordena por confidence score (com dampening Bayesiano)

### 6. Response

```json
{
  "parlamentares": [
    {
      "parlamentar_id": 42,
      "nome": "Fulano de Tal",
      "partido": "PT",
      "uf": "SP",
      "casa": "camara",
      "score": 85.0,
      "votos_comparados": 15,
      "concordou": 12,
      "presenca": 0.75,
      "confianca": "alta"
    }
  ],
  "partidos": [
    {
      "partido_id": 5,
      "sigla": "PT",
      "nome": "Partido dos Trabalhadores",
      "score": 78.3,
      "parlamentares_comparados": 45,
      "votos_comparados": 18,
      "concordou": 14,
      "confianca": "alta"
    }
  ]
}
```

---

## Comparações individuais

Além do ranking geral, existem endpoints para comparar um único parlamentar ou partido:

### `comparar_parlamentar()`

Mesma lógica de `_score_parlamentar()`, mas retorna `{score, concordou, discordou, total, presenca, confianca}`. Usado na página de detalhe do parlamentar.

### `comparar_partido()`

Mesma lógica de `_score_partido_hybrid()`, com `_min_compared()` consistente. Retorna `{score, concordou, discordou, total, parlamentares_comparados, confianca}`. Usado na página de detalhe do partido.

Ambos usam `_count_opinionated()` e `_min_compared()` para garantir thresholds consistentes com o ranking geral.
