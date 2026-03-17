export interface QuestionarioItem {
	proposicao_id: number;
	tipo: string;
	numero: number;
	ano: number;
	resumo: string;
	descricao_detalhada: string | null;
	tema: string;
	url_proposicao: string | null;
	casas: string[];
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
}

export interface PartidoMatchResult {
	partido_id: number;
	sigla: string;
	nome: string;
	score: number | null;
	parlamentares_comparados: number;
}

export interface MatchResponse {
	parlamentares: MatchResult[];
	partidos: PartidoMatchResult[];
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
