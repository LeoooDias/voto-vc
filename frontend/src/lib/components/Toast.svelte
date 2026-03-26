<script lang="ts">
	import { toasts, dismissToast } from '$lib/stores/toast';
</script>

{#if $toasts.length > 0}
	<div class="toast-container">
		{#each $toasts as toast (toast.id)}
			<div class="toast toast-{toast.type}" role="alert">
				<span class="toast-msg">{toast.message}</span>
				<button class="toast-close" onclick={() => dismissToast(toast.id)} aria-label="Fechar notificação">&times;</button>
			</div>
		{/each}
	</div>
{/if}

<style>
	.toast-container {
		position: fixed;
		top: 1rem;
		right: 1rem;
		z-index: 200;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		max-width: 400px;
	}

	.toast {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.75rem;
		padding: 0.75rem 1rem;
		border-radius: 10px;
		font-size: 0.875rem;
		line-height: 1.4;
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
		animation: slide-in 0.25s ease-out;
	}

	@keyframes slide-in {
		from {
			transform: translateX(100%);
			opacity: 0;
		}
		to {
			transform: translateX(0);
			opacity: 1;
		}
	}

	.toast-success {
		background: var(--color-favor);
		color: white;
	}

	.toast-error {
		background: var(--color-contra);
		color: white;
	}

	.toast-warning {
		background: var(--color-warning);
		color: white;
	}

	.toast-info {
		background: var(--link);
		color: white;
	}

	.toast-msg {
		flex: 1;
	}

	.toast-close {
		background: none;
		border: none;
		color: inherit;
		font-size: 1.25rem;
		cursor: pointer;
		padding: 0;
		line-height: 1;
		opacity: 0.8;
		min-width: 44px;
		min-height: 44px;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.toast-close:hover {
		opacity: 1;
	}
</style>
