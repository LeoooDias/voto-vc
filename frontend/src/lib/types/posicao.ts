export interface PosicaoProposicaoItem {
	proposicao_id: number;
	tipo: string;
	numero: number;
	ano: number;
	resumo: string | null;
	direcao: 'sim' | 'nao';
}

export interface PosicaoItem {
	id: number;
	slug: string;
	titulo: string;
	descricao: string;
	tema: string;
	ordem: number;
	proposicoes: PosicaoProposicaoItem[];
}

export interface RespostaPosicaoItem {
	posicao_id: number;
	voto: 'sim' | 'nao' | 'pular';
	peso: number;
}

export interface PosicaoInferida {
	posicao_id: number;
	slug: string;
	titulo: string;
	tema: string;
	stance: string;
	score_pct: number | null;
	n_voted: number;
	n_total: number;
}
