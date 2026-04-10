export interface CasaInfo {
	casa: string;
	url: string | null;
}

export interface QuestionarioItem {
	proposicao_id: number;
	tipo: string;
	numero: number;
	ano: number;
	resumo: string;
	descricao_detalhada: string | null;
	tema: string;
	casas: CasaInfo[];
}

export interface RespostaItem {
	proposicao_id: number;
	voto: 'sim' | 'nao' | 'pular';
	peso: number;
}

export interface MatchResult {
	parlamentar_id: number;
	nome: string;
	partido: string | null;
	uf: string;
	casa: string;
	sexo: string | null;
	foto_url: string | null;
	score: number;
	votos_comparados: number;
	concordou: number;
	presenca: number;
	confianca: 'alta' | 'media' | 'baixa';
}

export interface PartidoMatchResult {
	partido_id: number;
	sigla: string;
	nome: string;
	score: number | null;
	parlamentares_comparados: number;
	votos_comparados: number;
	concordou: number;
	confianca: 'alta' | 'media' | 'baixa';
}

export interface MatchResponse {
	parlamentares: MatchResult[];
	partidos: PartidoMatchResult[];
}

export interface VotoDetalhado {
	proposicao_id: number;
	tipo: string;
	numero: number;
	ano: number;
	resumo: string;
	voto: 'sim' | 'nao';
	peso: number;
}

export interface PerfilCompartilhado {
	slug: string;
	created_at: string;
	total_respostas: number;
	parlamentares: MatchResult[];
	partidos: PartidoMatchResult[];
	votos_detalhados: VotoDetalhado[];
}

export interface Parlamentar {
	id: number;
	nome_parlamentar: string;
	nome_civil: string;
	casa: string;
	uf: string;
	foto_url: string | null;
	partido: { sigla: string; nome: string } | null;
}
