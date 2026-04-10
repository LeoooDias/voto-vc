<script lang="ts">
	import { _ } from 'svelte-i18n';

	let { open = $bindable(false), url = '' } = $props();
	let copied = $state(false);

	function close() {
		open = false;
		copied = false;
	}

	async function copyLink() {
		try {
			await navigator.clipboard.writeText(url);
			copied = true;
			setTimeout(() => (copied = false), 2000);
		} catch {
			// Fallback
			const input = document.querySelector<HTMLInputElement>('.share-url-input');
			if (input) {
				input.select();
				document.execCommand('copy');
				copied = true;
				setTimeout(() => (copied = false), 2000);
			}
		}
	}

	function shareWhatsApp() {
		const msg = $_('compartilhar.mensagem');
		const text = `${msg}\n${url}`;
		window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank');
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') close();
	}
</script>

<svelte:window onkeydown={handleKeydown} />

{#if open}
	<button class="backdrop" onclick={close} aria-label={$_('common.fechar')}></button>
	<div class="modal" role="dialog" aria-modal="true" aria-labelledby="share-title">
		<div class="modal-header">
			<h2 id="share-title">{$_('compartilhar.titulo')}</h2>
			<button class="close-btn" onclick={close} aria-label={$_('common.fechar')}>&times;</button>
		</div>

		<div class="share-content">
			<div class="url-row">
				<input
					class="share-url-input"
					type="text"
					readonly
					value={url}
					onclick={(e) => (e.target as HTMLInputElement).select()}
				/>
				<button class="copy-btn" onclick={copyLink}>
					{copied ? $_('compartilhar.copiado') : $_('compartilhar.copiar')}
				</button>
			</div>

			<button class="whatsapp-btn" onclick={shareWhatsApp}>
				{$_('compartilhar.whatsapp')}
			</button>
		</div>
	</div>
{/if}

<style>
	.backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.5);
		z-index: 1000;
		border: none;
		cursor: pointer;
	}

	.modal {
		position: fixed;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: 0;
		z-index: 1001;
		width: min(440px, calc(100vw - 2rem));
		max-height: calc(100vh - 4rem);
		overflow-y: auto;
	}

	.modal-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 1.25rem 1.5rem;
		border-bottom: 1px solid var(--border);
	}

	.modal-header h2 {
		font-family: var(--font-heading);
		font-size: 1rem;
		font-weight: 800;
		letter-spacing: -0.02em;
		margin: 0;
		color: var(--text-primary);
	}

	.close-btn {
		background: none;
		border: none;
		font-size: 1.5rem;
		cursor: pointer;
		color: var(--text-secondary);
		line-height: 1;
		padding: 0;
	}

	.close-btn:hover {
		color: var(--text-primary);
	}

	.share-content {
		padding: 1.5rem;
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.url-row {
		display: flex;
		gap: 0;
	}

	.share-url-input {
		flex: 1;
		padding: 0.75rem;
		border: 1.5px solid var(--border);
		border-right: none;
		border-radius: 0;
		background: var(--bg-page);
		color: var(--text-primary);
		font-family: var(--font-heading);
		font-size: 0.813rem;
		font-weight: 500;
		outline: none;
	}

	.copy-btn {
		padding: 0.75rem 1rem;
		border: 1.5px solid var(--text-primary);
		border-radius: 0;
		background: var(--text-primary);
		color: var(--bg-page);
		font-family: var(--font-heading);
		font-size: 0.688rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		cursor: pointer;
		white-space: nowrap;
		transition: opacity 0.15s;
	}

	.copy-btn:hover {
		opacity: 0.85;
	}

	.whatsapp-btn {
		width: 100%;
		padding: 0.875rem;
		border: 1.5px solid #25d366;
		border-radius: 0;
		background: #25d366;
		color: #fff;
		font-family: var(--font-heading);
		font-size: 0.813rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		cursor: pointer;
		transition: opacity 0.15s;
	}

	.whatsapp-btn:hover {
		opacity: 0.9;
	}
</style>
