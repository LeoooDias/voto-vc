<script lang="ts">
	/**
	 * 5-position vote intensity slider.
	 *
	 * Positions map to:
	 *   1 = Fortemente Contra  (nao, peso 1.0)
	 *   2 = Contra             (nao, peso 0.5)
	 *   3 = Neutro             (sim, peso 0.0)
	 *   4 = A favor            (sim, peso 0.5)
	 *   5 = Fortemente A favor (sim, peso 1.0)
	 */

	interface Props {
		value?: number | null;
		onvote: (voto: 'sim' | 'nao', peso: number) => void;
		onpular: () => void;
		compact?: boolean;
	}

	const POSITIONS = [
		{ pos: 1, label: 'Forte', voto: 'nao' as const, peso: 1.0, cls: 'p1' },
		{ pos: 2, label: 'Contra', voto: 'nao' as const, peso: 0.5, cls: 'p2' },
		{ pos: 3, label: 'Neutro', voto: 'sim' as const, peso: 0.0, cls: 'p3' },
		{ pos: 4, label: 'A favor', voto: 'sim' as const, peso: 0.5, cls: 'p4' },
		{ pos: 5, label: 'Forte', voto: 'sim' as const, peso: 1.0, cls: 'p5' },
	];

	const FULL_LABELS: Record<number, string> = {
		1: 'Fortemente Contra',
		2: 'Contra',
		3: 'Neutro',
		4: 'A favor',
		5: 'Fortemente A favor',
	};

	let { value = null, onvote, onpular, compact = false }: Props = $props();

	function select(p: (typeof POSITIONS)[number]) {
		onvote(p.voto, p.peso);
	}
</script>

<div class="vote-slider" class:compact>
	<div class="slider-row">
		<div class="track-bg">
			<div class="track-fill"></div>
		</div>
		{#each POSITIONS as p}
			<button
				class="pos-btn {p.cls}"
				class:active={value === p.pos}
				onclick={() => select(p)}
				title={FULL_LABELS[p.pos]}
			>
				<span class="dot"></span>
				<span class="lbl">{p.label}</span>
			</button>
		{/each}
	</div>
	{#if !compact}
		<button class="pular-btn" onclick={onpular}>Pular</button>
	{/if}
</div>

<style>
	.vote-slider {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.75rem;
		width: 100%;
	}

	.slider-row {
		display: flex;
		width: 100%;
		justify-content: space-between;
		position: relative;
		padding: 0 4px;
	}

	/* Track behind dots — absolutely positioned */
	.track-bg {
		position: absolute;
		top: 12px;
		left: 24px;
		right: 24px;
		height: 4px;
		border-radius: 2px;
		overflow: hidden;
		background: var(--border);
	}

	.track-fill {
		position: absolute;
		inset: 0;
		background: linear-gradient(to right, #dc2626, #f87171, #d4d4d4, #4ade80, #16a34a);
		opacity: 0.4;
	}

	.pos-btn {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.3rem;
		background: none;
		border: none;
		cursor: pointer;
		padding: 0;
		position: relative;
		z-index: 1;
		width: 48px;
	}

	.dot {
		width: 28px;
		height: 28px;
		border-radius: 50%;
		border: 3px solid var(--border);
		background: var(--bg-card);
		transition: all 0.15s ease;
		flex-shrink: 0;
	}

	.pos-btn:hover .dot {
		transform: scale(1.1);
	}

	/* Colors per position */
	.p1 .dot { border-color: #dc2626; }
	.p2 .dot { border-color: #f87171; }
	.p3 .dot { border-color: #a3a3a3; }
	.p4 .dot { border-color: #4ade80; }
	.p5 .dot { border-color: #16a34a; }

	.pos-btn.active .dot {
		transform: scale(1.15);
	}

	.p1.active .dot { background: #dc2626; border-color: #dc2626; box-shadow: 0 0 0 3px #dc262633; }
	.p2.active .dot { background: #f87171; border-color: #f87171; box-shadow: 0 0 0 3px #f8717133; }
	.p3.active .dot { background: #a3a3a3; border-color: #a3a3a3; box-shadow: 0 0 0 3px #a3a3a333; }
	.p4.active .dot { background: #4ade80; border-color: #4ade80; box-shadow: 0 0 0 3px #4ade8033; }
	.p5.active .dot { background: #16a34a; border-color: #16a34a; box-shadow: 0 0 0 3px #16a34a33; }

	.lbl {
		font-size: 0.65rem;
		font-weight: 600;
		color: var(--text-secondary);
		text-align: center;
		line-height: 1.15;
		white-space: nowrap;
		transition: color 0.15s;
	}

	.pos-btn.active .lbl {
		color: var(--text-primary);
	}

	.p1.active .lbl { color: #dc2626; }
	.p2.active .lbl { color: #f87171; }
	.p3.active .lbl { color: #737373; }
	.p4.active .lbl { color: #22c55e; }
	.p5.active .lbl { color: #16a34a; }

	.pular-btn {
		padding: 0.35rem 1.25rem;
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: 8px;
		font-size: 0.8rem;
		font-weight: 600;
		color: var(--text-secondary);
		cursor: pointer;
		transition: border-color 0.2s, color 0.2s;
	}

	.pular-btn:hover {
		border-color: var(--text-secondary);
		color: var(--text-primary);
	}

	/* Compact mode (for perfil re-vote) */
	.compact .dot {
		width: 20px;
		height: 20px;
		border-width: 2px;
	}

	.compact .pos-btn {
		width: 40px;
	}

	.compact .lbl {
		font-size: 0.55rem;
	}

	.compact .track-bg {
		top: 9px;
		left: 20px;
		right: 20px;
		height: 3px;
	}

	.compact .slider-row {
		padding: 0 2px;
	}

	/* Mobile: slightly larger touch targets */
	@media (max-width: 480px) {
		.pos-btn {
			width: 44px;
		}

		.dot {
			width: 30px;
			height: 30px;
		}

		.track-bg {
			top: 13px;
		}
	}
</style>
