<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { checkAuth } from '$lib/stores/auth';
	import { migrarRespostasAnonimas, carregarRespostas, respostas } from '$lib/stores/questionario';
	import { migrarPosicaoRespostasAnonimas } from '$lib/stores/posicoes';

	onMount(async () => {
		const user = await checkAuth();
		if (user) {
			const hadRespostas = await migrarRespostasAnonimas();
			await migrarPosicaoRespostasAnonimas();

			// Reload responses from backend into store
			const saved = await carregarRespostas();
			if (saved.length > 0) {
				respostas.set(saved);
				goto('/perfil');
				return;
			}

			if (hadRespostas) {
				goto('/perfil');
				return;
			}
		}
		goto('/');
	});
</script>

<div class="callback">
	<p>Autenticando...</p>
</div>

<style>
	.callback {
		display: flex;
		justify-content: center;
		align-items: center;
		min-height: 60vh;
		color: var(--text-secondary);
	}
</style>
