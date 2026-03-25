export const UFS = [
	{ sigla: 'AC', nome: 'Acre' },
	{ sigla: 'AL', nome: 'Alagoas' },
	{ sigla: 'AP', nome: 'Amapá' },
	{ sigla: 'AM', nome: 'Amazonas' },
	{ sigla: 'BA', nome: 'Bahia' },
	{ sigla: 'CE', nome: 'Ceará' },
	{ sigla: 'DF', nome: 'Distrito Federal' },
	{ sigla: 'ES', nome: 'Espírito Santo' },
	{ sigla: 'GO', nome: 'Goiás' },
	{ sigla: 'MA', nome: 'Maranhão' },
	{ sigla: 'MT', nome: 'Mato Grosso' },
	{ sigla: 'MS', nome: 'Mato Grosso do Sul' },
	{ sigla: 'MG', nome: 'Minas Gerais' },
	{ sigla: 'PA', nome: 'Pará' },
	{ sigla: 'PB', nome: 'Paraíba' },
	{ sigla: 'PR', nome: 'Paraná' },
	{ sigla: 'PE', nome: 'Pernambuco' },
	{ sigla: 'PI', nome: 'Piauí' },
	{ sigla: 'RJ', nome: 'Rio de Janeiro' },
	{ sigla: 'RN', nome: 'Rio Grande do Norte' },
	{ sigla: 'RS', nome: 'Rio Grande do Sul' },
	{ sigla: 'RO', nome: 'Rondônia' },
	{ sigla: 'RR', nome: 'Roraima' },
	{ sigla: 'SC', nome: 'Santa Catarina' },
	{ sigla: 'SP', nome: 'São Paulo' },
	{ sigla: 'SE', nome: 'Sergipe' },
	{ sigla: 'TO', nome: 'Tocantins' }
] as const;

export const UF_SIGLAS = UFS.map((u) => u.sigla);

export const TEMAS: Record<string, { label: string; cor: string }> = {
	economia: { label: 'Economia', cor: '#2563EB' },
	tributacao: { label: 'Tributação', cor: '#7C3AED' },
	saude: { label: 'Saúde', cor: '#DC2626' },
	educacao: { label: 'Educação', cor: '#EA580C' },
	'meio-ambiente': { label: 'Meio Ambiente', cor: '#16A34A' },
	seguranca: { label: 'Segurança', cor: '#475569' },
	'direitos-humanos': { label: 'Direitos Humanos', cor: '#DB2777' },
	trabalho: { label: 'Trabalho', cor: '#CA8A04' },
	agricultura: { label: 'Agricultura', cor: '#65A30D' },
	defesa: { label: 'Defesa', cor: '#0F766E' },
	tecnologia: { label: 'Tecnologia', cor: '#6366F1' },
	corrupcao: { label: 'Transparência', cor: '#B91C1C' },
	previdencia: { label: 'Previdência', cor: '#78716C' },
	habitacao: { label: 'Habitação', cor: '#0891B2' },
	transporte: { label: 'Transporte', cor: '#F59E0B' },
	cultura: { label: 'Cultura', cor: '#A855F7' },
	geral: { label: 'Legislação', cor: '#6B7280' }
};

export function getTema(slug: string | null | undefined) {
	if (!slug) return TEMAS.geral;
	return TEMAS[slug] ?? TEMAS.geral;
}

export interface PosicaoCategoria {
	id: string;
	label: string;
	cor: string;
	ordens: number[];
}

export const POSICAO_CATEGORIAS: PosicaoCategoria[] = [
	{
		id: 'economia',
		label: 'Economia & Tributação',
		cor: '#CA8A04',
		ordens: [1, 2, 3, 4, 5]
	},
	{
		id: 'seguranca',
		label: 'Segurança & Direitos Humanos',
		cor: '#2563EB',
		ordens: [6, 7, 11, 12, 13]
	},
	{
		id: 'social',
		label: 'Educação, Saúde & Meio Ambiente',
		cor: '#16A34A',
		ordens: [9, 10, 17, 18, 19]
	},
	{
		id: 'outros',
		label: 'Outros temas',
		cor: '#6B7280',
		ordens: [8, 14, 15, 16, 20]
	}
];

export const TIER1 = 10;
export const TIER2 = 25;
export const TIER3 = 50;

/** Formata número como percentual brasileiro: vírgula decimal, sempre 1 casa. Ex: 75,0% */
export function fmtPct(value: number | null | undefined): string {
	if (value == null) return 'N/A';
	return value.toFixed(1).replace('.', ',') + '%';
}
