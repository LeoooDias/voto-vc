import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, fetch }) => {
	const res = await fetch(`/api/perfil/${params.slug}`);
	if (!res.ok) {
		error(404, 'Perfil não encontrado');
	}
	const perfil = await res.json();
	return { perfil, slug: params.slug };
};
