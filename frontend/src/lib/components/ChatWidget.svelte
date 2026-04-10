<script lang="ts">
	import { _, locale } from 'svelte-i18n';
	import { marked } from 'marked';

	interface Props {
		proposicaoId?: number;
		posicaoId?: number;
		proposicaoTitulo: string;
		inline?: boolean;
	}

	interface ChatMessage {
		role: 'user' | 'assistant';
		content: string;
	}

	let { proposicaoId, posicaoId, proposicaoTitulo, inline = false }: Props = $props();

	const chatEndpoint = $derived(
		posicaoId ? `/api/chat/posicao/${posicaoId}` : `/api/chat/proposicao/${proposicaoId}`
	);
	const entityId = $derived(posicaoId ?? proposicaoId ?? 0);

	let isOpen = $state(false);
	let isExpanded = $state(false);
	let messages: ChatMessage[] = $state([]);
	let inputText = $state('');
	let isStreaming = $state(false);
	let error = $state('');
	let messagesEl: HTMLDivElement | undefined = $state();

	// Reset chat when entity changes
	let lastSeenId: number | null = $state(null);
	$effect(() => {
		const eid = entityId;
		if (lastSeenId !== null && eid !== lastSeenId) {
			messages = [];
			error = '';
			inputText = '';
			isStreaming = false;
		}
		lastSeenId = eid;
	});

	function toggle() {
		isOpen = !isOpen;
		if (isOpen) {
			// Focus input after opening
			setTimeout(() => {
				const input = document.querySelector('.chat-input') as HTMLInputElement;
				input?.focus();
			}, 100);
		}
	}

	function close() {
		isOpen = false;
		isExpanded = false;
	}

	function toggleExpand() {
		isExpanded = !isExpanded;
	}

	function scrollToBottom() {
		if (messagesEl) {
			setTimeout(() => {
				messagesEl!.scrollTop = messagesEl!.scrollHeight;
			}, 10);
		}
	}

	async function sendMessage() {
		const text = inputText.trim();
		if (!text || isStreaming) return;

		error = '';
		inputText = '';

		// Add user message
		messages = [...messages, { role: 'user', content: text }];
		scrollToBottom();

		// Prepare history (exclude current message)
		const history = messages.slice(0, -1).map((m) => ({
			role: m.role,
			content: m.content
		}));

		// Add placeholder assistant message
		messages = [...messages, { role: 'assistant', content: '' }];
		isStreaming = true;

		try {
			const res = await fetch(chatEndpoint, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ message: text, history, lang: $locale ?? 'pt-BR' })
			});

			if (res.status === 429) {
				error = $_('chat.erroLimite');
				messages = messages.slice(0, -1);
				isStreaming = false;
				return;
			}

			if (res.status === 503) {
				error = $_('chat.erroIndisponivel');
				messages = messages.slice(0, -1);
				isStreaming = false;
				return;
			}

			if (!res.ok) {
				error = $_('chat.erroConexao');
				messages = messages.slice(0, -1);
				isStreaming = false;
				return;
			}

			const reader = res.body?.getReader();
			if (!reader) {
				error = $_('chat.erroStreaming');
				messages = messages.slice(0, -1);
				isStreaming = false;
				return;
			}

			const decoder = new TextDecoder();
			let buffer = '';

			while (true) {
				const { done, value } = await reader.read();
				if (done) break;

				buffer += decoder.decode(value, { stream: true });

				// Parse SSE events from buffer
				const lines = buffer.split('\n');
				buffer = lines.pop() ?? '';

				for (const line of lines) {
					if (!line.startsWith('data: ')) continue;
					try {
						const data = JSON.parse(line.slice(6));
						if (data.text) {
							// Update last message (assistant)
							const last = messages[messages.length - 1];
							if (last && last.role === 'assistant') {
								messages = [
									...messages.slice(0, -1),
									{ ...last, content: last.content + data.text }
								];
								scrollToBottom();
							}
						}
						if (data.error) {
							error = data.error;
						}
						if (data.done) {
							// Stream complete
						}
					} catch {
						// Skip malformed SSE lines
					}
				}
			}
		} catch (e) {
			error = $_('chat.erroConexaoTentar');
			// Remove empty assistant placeholder if no content was received
			const last = messages[messages.length - 1];
			if (last?.role === 'assistant' && !last.content) {
				messages = messages.slice(0, -1);
			}
		} finally {
			isStreaming = false;
			scrollToBottom();
		}
	}

	// Configure marked for chat: no paragraph wrapping for single lines, links open in new tab
	marked.use({
		renderer: {
			link({ href, text }) {
				return `<a href="${href}" target="_blank" rel="noopener">${text}</a>`;
			}
		},
		breaks: true,
		gfm: true,
	});

	function renderMarkdown(text: string): string {
		return marked.parse(text, { async: false }) as string;
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			sendMessage();
		}
	}

</script>

{#if inline}
	<button class="chat-inline-btn" onclick={toggle} aria-label={posicaoId ? $_('chat.perguntePosicao') : $_('chat.pergunteProposicao')}>
		<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
		<span>{posicaoId ? $_('chat.perguntePosicao') : $_('chat.pergunteProposicao')}</span>
	</button>
{:else}
	<button class="chat-fab" class:open={isOpen} onclick={toggle} aria-label={isOpen ? $_('chat.fechar') : $_('chat.abrir')}>
		{#if isOpen}
			<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
		{:else}
			<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
			<span class="fab-label">{posicaoId ? $_('chat.perguntePosicao') : $_('chat.pergunteProposicao')}</span>
		{/if}
	</button>
{/if}

<!-- Chat modal -->
{#if isOpen}
	<button class="chat-backdrop" onclick={close} aria-label={$_('chat.fechar')}></button>
	<div class="chat-modal" class:expanded={isExpanded} role="dialog" aria-label={posicaoId ? $_('chat.chatSobrePosicao') : $_('chat.chatSobreProposicao')}>
		<div class="chat-header">
			<div class="chat-title">
				<span class="chat-icon">
					<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
				</span>
				<span class="chat-prop-title">{proposicaoTitulo}</span>
			</div>
			<div class="chat-header-actions">
				<button class="chat-expand" onclick={toggleExpand} aria-label={isExpanded ? $_('chat.reduzir') : $_('chat.expandir')}>
					{#if isExpanded}
						<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="4 14 10 14 10 20"/><polyline points="20 10 14 10 14 4"/><line x1="14" y1="10" x2="21" y2="3"/><line x1="3" y1="21" x2="10" y2="14"/></svg>
					{:else}
						<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg>
					{/if}
				</button>
				<button class="chat-close" onclick={close} aria-label={$_('chat.fechar')}>
					<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
				</button>
			</div>
		</div>

		<div class="chat-messages" bind:this={messagesEl} aria-live="polite">
				{#if messages.length === 0}
					<div class="chat-empty">
						<p>{posicaoId ? $_('chat.pergunteQualquerPosicao') : $_('chat.pergunteQualquerProposicao')}</p>
						<div class="suggestions">
							{#if posicaoId}
								<button class="suggestion" onclick={() => { inputText = $_('chat.sugestaoExplicar'); sendMessage(); }}>{$_('chat.sugestaoExplicar')}</button>
								<button class="suggestion" onclick={() => { inputText = $_('chat.sugestaoArgumentos'); sendMessage(); }}>{$_('chat.sugestaoArgumentos')}</button>
								<button class="suggestion" onclick={() => { inputText = $_('chat.sugestaoImpacto'); sendMessage(); }}>{$_('chat.sugestaoImpacto')}</button>
							{:else}
								<button class="suggestion" onclick={() => { inputText = $_('chat.sugestaoResumo'); sendMessage(); }}>{$_('chat.sugestaoResumo')}</button>
								<button class="suggestion" onclick={() => { inputText = $_('chat.sugestaoArgumentos'); sendMessage(); }}>{$_('chat.sugestaoArgumentos')}</button>
								<button class="suggestion" onclick={() => { inputText = $_('chat.sugestaoImpacto'); sendMessage(); }}>{$_('chat.sugestaoImpacto')}</button>
							{/if}
						</div>
					</div>
				{/if}

				{#each messages as msg}
					<div class="chat-msg" class:user={msg.role === 'user'} class:assistant={msg.role === 'assistant'}>
						{#if msg.role === 'assistant' && !msg.content && isStreaming}
							<span class="typing-indicator">
								<span></span><span></span><span></span>
							</span>
						{:else if msg.role === 'user'}
							<div class="msg-content">{msg.content}</div>
						{:else}
							<div class="msg-content markdown">{@html renderMarkdown(msg.content)}</div>
						{/if}
					</div>
				{/each}

				{#if error}
					<div class="chat-error">{error}</div>
				{/if}
			</div>

			<div class="chat-input-area">
				<input
					class="chat-input"
					type="text"
					placeholder={$_('chat.placeholder')}
					bind:value={inputText}
					onkeydown={handleKeydown}
					disabled={isStreaming}
				/>
				<button
					class="chat-send"
					onclick={sendMessage}
					disabled={isStreaming || !inputText.trim()}
					aria-label="Enviar"
				>
					<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
				</button>
		</div>
	</div>
{/if}

<style>
	/* Inline button (inside card) */
	.chat-inline-btn {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		background: none;
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 0.4rem 0.75rem;
		color: var(--link);
		font-size: 0.8rem;
		font-weight: 600;
		cursor: pointer;
		margin-top: 0.75rem;
		transition: border-color 0.2s, background 0.2s;
	}

	.chat-inline-btn:hover {
		border-color: var(--link);
		background: color-mix(in srgb, var(--link) 5%, transparent);
	}

	/* Floating Action Button */
	.chat-fab {
		position: fixed;
		bottom: 1.5rem;
		right: 1.5rem;
		height: 44px;
		padding: 0 1rem;
		border-radius: 22px;
		background: var(--link);
		color: white;
		border: none;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4);
		transition: transform 0.2s, background 0.2s;
		z-index: 1000;
	}

	.fab-label {
		font-size: 0.8rem;
		font-weight: 600;
		white-space: nowrap;
	}

	.chat-fab:hover {
		transform: scale(1.03);
		background: var(--link-hover);
	}

	.chat-fab.open {
		padding: 0;
		width: 44px;
		border-radius: 50%;
		background: #64748b;
		box-shadow: 0 4px 12px rgba(100, 116, 139, 0.4);
	}

	/* Backdrop */
	.chat-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.3);
		z-index: 1001;
		border: none;
		cursor: default;
		padding: 0;
		margin: 0;
		width: 100%;
		height: 100%;
	}

	/* Modal */
	.chat-modal {
		position: fixed;
		bottom: 5rem;
		right: 1.5rem;
		width: 400px;
		max-height: 550px;
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: 0;
		box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
		display: flex;
		flex-direction: column;
		z-index: 1002;
		overflow: hidden;
	}

	/* Tablet breakpoint */
	@media (min-width: 481px) and (max-width: 1024px) {
		.chat-modal {
			width: calc(100vw - 3rem);
			max-width: 500px;
		}
	}

	/* Expanded state — desktop only */
	@media (min-width: 481px) {
		.chat-modal.expanded {
			width: 700px;
			max-height: 80vh;
			bottom: 50%;
			right: 50%;
			transform: translate(50%, 50%);
			border-radius: 20px;
		}
	}

	/* Mobile: full screen */
	@media (max-width: 480px) {
		.chat-modal {
			inset: 0;
			width: 100%;
			max-height: 100%;
			border-radius: 0;
			bottom: 0;
			right: 0;
		}

		.chat-fab {
			bottom: 1rem;
			right: 1rem;
		}
	}

	/* Header */
	.chat-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.75rem 1rem;
		border-bottom: 1px solid var(--border);
		background: var(--bg-page);
	}

	.chat-title {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		min-width: 0;
	}

	.chat-icon {
		color: var(--link);
		flex-shrink: 0;
		display: flex;
	}

	.chat-prop-title {
		font-size: 0.8rem;
		font-weight: 600;
		color: var(--text-primary);
		white-space: normal;
		overflow: hidden;
		text-overflow: ellipsis;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
	}

	.chat-header-actions {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		flex-shrink: 0;
	}

	.chat-expand {
		background: none;
		border: none;
		color: var(--text-secondary);
		cursor: pointer;
		padding: 0.5rem;
		display: none;
		border-radius: 4px;
	}

	.chat-expand:hover {
		color: var(--text-primary);
		background: var(--border);
	}

	@media (min-width: 481px) {
		.chat-expand {
			display: flex;
		}
	}

	.chat-close {
		background: none;
		border: none;
		color: var(--text-secondary);
		cursor: pointer;
		padding: 0.5rem;
		display: flex;
		flex-shrink: 0;
		border-radius: 4px;
	}

	.chat-close:hover {
		color: var(--text-primary);
		background: var(--border);
	}

	/* Messages */
	.chat-messages {
		flex: 1;
		overflow-y: auto;
		padding: 1rem;
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		min-height: 200px;
	}

	.chat-empty {
		text-align: center;
		color: var(--text-secondary);
		padding: 1rem 0;
	}

	.chat-empty p {
		font-size: 0.85rem;
		margin-bottom: 1rem;
	}

	.suggestions {
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
	}

	.suggestion {
		background: var(--bg-page);
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 0.5rem 0.75rem;
		font-size: 0.8rem;
		color: var(--link);
		cursor: pointer;
		text-align: left;
		transition: border-color 0.2s;
	}

	.suggestion:hover {
		border-color: var(--link);
	}

	.chat-msg {
		max-width: 85%;
	}

	.chat-msg.user {
		align-self: flex-end;
	}

	.chat-msg.assistant {
		align-self: flex-start;
	}

	.msg-content {
		padding: 0.6rem 0.9rem;
		border-radius: 0;
		font-size: 0.85rem;
		line-height: 1.5;
		word-break: break-word;
	}

	.user .msg-content {
		white-space: pre-wrap;
		background: var(--link);
		color: white;
		border-bottom-right-radius: 4px;
	}

	.assistant .msg-content {
		background: var(--bg-page);
		color: var(--text-primary);
		border: 1px solid var(--border);
		border-bottom-left-radius: 4px;
	}

	/* Markdown inside assistant messages */
	.msg-content.markdown :global(p) {
		margin: 0 0 0.5em;
	}

	.msg-content.markdown :global(p:last-child) {
		margin-bottom: 0;
	}

	.msg-content.markdown :global(ul),
	.msg-content.markdown :global(ol) {
		margin: 0.3em 0;
		padding-left: 1.4em;
	}

	.msg-content.markdown :global(li) {
		margin: 0.15em 0;
	}

	.msg-content.markdown :global(strong) {
		font-weight: 700;
	}

	.msg-content.markdown :global(em) {
		font-style: italic;
	}

	.msg-content.markdown :global(code) {
		background: var(--color-code-bg);
		padding: 0.1em 0.3em;
		border-radius: 3px;
		font-size: 0.8em;
	}

	.msg-content.markdown :global(a) {
		color: var(--link);
		text-decoration: underline;
	}

	.msg-content.markdown :global(h1),
	.msg-content.markdown :global(h2),
	.msg-content.markdown :global(h3) {
		font-size: 0.9rem;
		font-weight: 700;
		margin: 0.5em 0 0.25em;
	}

	.msg-content.markdown :global(blockquote) {
		border-left: 3px solid var(--border);
		margin: 0.3em 0;
		padding-left: 0.6em;
		color: var(--text-secondary);
	}

	.chat-error {
		font-size: 0.8rem;
		color: var(--color-contra);
		text-align: center;
		padding: 0.5rem;
	}

	/* Typing indicator */
	.typing-indicator {
		display: flex;
		gap: 4px;
		padding: 0.75rem 1rem;
		background: var(--bg-page);
		border: 1px solid var(--border);
		border-radius: 0;
		border-bottom-left-radius: 4px;
	}

	.typing-indicator span {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: var(--text-secondary);
		animation: typing 1.2s ease-in-out infinite;
	}

	.typing-indicator span:nth-child(2) {
		animation-delay: 0.2s;
	}

	.typing-indicator span:nth-child(3) {
		animation-delay: 0.4s;
	}

	@keyframes typing {
		0%, 60%, 100% { opacity: 0.3; transform: translateY(0); }
		30% { opacity: 1; transform: translateY(-3px); }
	}

	/* Input area */
	.chat-input-area {
		display: flex;
		gap: 0.5rem;
		padding: 0.75rem 1rem;
		border-top: 1px solid var(--border);
		background: var(--bg-page);
	}

	.chat-input {
		flex: 1;
		padding: 0.6rem 0.75rem;
		border: 1px solid var(--border);
		border-radius: 8px;
		background: var(--bg-card);
		color: var(--text-primary);
		font-size: 0.85rem;
		outline: none;
		transition: border-color 0.2s;
	}

	.chat-input:focus {
		border-color: var(--link);
	}

	.chat-input:disabled {
		opacity: 0.6;
	}

	.chat-send {
		width: 38px;
		height: 38px;
		border-radius: 8px;
		background: var(--link);
		color: white;
		border: none;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
		transition: background 0.2s;
	}

	.chat-send:hover:not(:disabled) {
		background: var(--link-hover);
	}

	.chat-send:disabled {
		opacity: 0.4;
		cursor: default;
	}
</style>
