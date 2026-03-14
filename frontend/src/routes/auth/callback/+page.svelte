<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { checkAuth } from '$lib/stores/auth';

	onMount(async () => {
		await checkAuth();
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
