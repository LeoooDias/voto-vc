export interface QuestionarioItem {
	proposicao_id: number;
	tipo: string;
	numero: number;
	ano: number;
	resumo: string;
	descricao_detalhada: string | null;
	tema: string;
	url_camara: string | null;
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
	foto_url: string | null;
	score: number;
	votos_comparados: number;
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
