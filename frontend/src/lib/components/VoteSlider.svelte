<script lang="ts">
	/**
	 * 5-position vote intensity slider.
	 *
	 * Positions map to:
	 *   1 = Contra       (nao, peso 1.00)
	 *   2 = Contra leve  (nao, peso 0.50)
	 *   3 = Neutro       (sim, peso 0.00)
	 *   4 = A favor leve (sim, peso 0.50)
	 *   5 = A favor      (sim, peso 1.00)
	 *
	 * In normal mode, clicking a dot only selects it visually (onselect).
	 * The parent is responsible for confirming the vote.
	 * In compact mode (perfil re-vote), clicking a dot fires onvote directly.
	 */

	interface Props {
		value?: number | null;
		onselect?: (pos: number) => void;
		onvote?: (voto: 'sim' | 'nao', peso: number) => void;
		compact?: boolean;
	}

	interface Position {
		pos: number;
		voto: 'sim' | 'nao';
		peso: number;
		label?: string;
	}

	const POSITIONS: Position[] = [
		{ pos: 1, voto: 'nao', peso: 1.0, label: 'Contra' },
		{ pos: 2, voto: 'nao', peso: 0.5, label: 'Contra leve' },
		{ pos: 3, voto: 'sim', peso: 0.0, label: 'Neutro' },
		{ pos: 4, voto: 'sim', peso: 0.5, label: 'A favor leve' },
		{ pos: 5, voto: 'sim', peso: 1.0, label: 'A favor' },
	];

	const TOOLTIP: Record<number, string> = {
		1: 'Contra',
		2: 'Contra (leve)',
		3: 'Neutro',
		4: 'A favor (leve)',
		5: 'A favor',
	};

	let { value = null, onselect, onvote, compact = false }: Props = $props();

	function handleClick(p: Position) {
		if (compact && onvote) {
			// Compact mode: fire vote directly
			onvote(p.voto, p.peso);
		} else if (onselect) {
			// Normal mode: just select visually
			onselect(p.pos);
		}
	}

	function colorForPos(pos: number): string {
		const colors: Record<number, string> = {
			1: '#dc2626',
			2: '#f87171',
			3: '#a3a3a3',
			4: '#4ade80',
			5: '#16a34a',
		};
		return colors[pos] ?? '#a3a3a3';
	}
</script>

<div class="vote-slider" class:compact>
	<div class="labels-row">
		<span class="end-label left">Contra</span>
		<span class="end-label center">Neutro</span>
		<span class="end-label right">A favor</span>
	</div>
	<div class="slider-row">
		<div class="track-bg">
			<div class="track-fill"></div>
		</div>
		{#each POSITIONS as p}
			<button
				class="pos-btn"
				class:active={value === p.pos}
				class:endpoint={p.pos === 1 || p.pos === 3 || p.pos === 5}
				onclick={() => handleClick(p)}
				title={TOOLTIP[p.pos]}
				style:--dot-color={colorForPos(p.pos)}
			>
				<span class="dot"></span>
			</button>
		{/each}
	</div>
</div>

<style>
	.vote-slider {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.4rem;
		width: 100%;
	}

	.labels-row {
		display: flex;
		width: 100%;
		justify-content: space-between;
		align-items: center;
		padding: 0 2px;
	}

	.end-label {
		font-size: 0.7rem;
		font-weight: 600;
		color: var(--text-secondary);
	}

	.end-label.left { color: #dc2626; }
	.end-label.center { color: #737373; }
	.end-label.right { color: #16a34a; }

	.slider-row {
		display: flex;
		width: 100%;
		justify-content: space-between;
		position: relative;
		padding: 0 4px;
	}

	.track-bg {
		position: absolute;
		top: 50%;
		left: 20px;
		right: 20px;
		height: 4px;
		margin-top: -2px;
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
		align-items: center;
		justify-content: center;
		background: none;
		border: none;
		cursor: pointer;
		padding: 4px 0;
		position: relative;
		z-index: 1;
		width: 36px;
	}

	.dot {
		width: 18px;
		height: 18px;
		border-radius: 50%;
		border: 2.5px solid var(--dot-color, var(--border));
		background: var(--bg-card);
		transition: all 0.15s ease;
		flex-shrink: 0;
	}

	.pos-btn.endpoint .dot {
		width: 24px;
		height: 24px;
		border-width: 3px;
	}

	.pos-btn:hover .dot {
		transform: scale(1.15);
	}

	.pos-btn.active .dot {
		background: var(--dot-color);
		border-color: var(--dot-color);
		box-shadow: 0 0 0 3px color-mix(in srgb, var(--dot-color) 20%, transparent);
		transform: scale(1.2);
	}

	.pos-btn.active.endpoint .dot {
		transform: scale(1.25);
	}

	/* Compact mode (for perfil re-vote) */
	.compact .dot {
		width: 14px;
		height: 14px;
		border-width: 2px;
	}

	.compact .pos-btn.endpoint .dot {
		width: 18px;
		height: 18px;
		border-width: 2.5px;
	}

	.compact .pos-btn {
		width: 26px;
	}

	.compact .end-label {
		font-size: 0.6rem;
	}

	.compact .track-bg {
		left: 14px;
		right: 14px;
		height: 3px;
		margin-top: -1.5px;
	}

	.compact .slider-row {
		padding: 0 2px;
	}

	.compact .labels-row {
		padding: 0 0;
	}

	/* Mobile */
	@media (max-width: 480px) {
		.pos-btn {
			width: 30px;
		}

		.dot {
			width: 24px;
			height: 24px;
		}

		.pos-btn.endpoint .dot {
			width: 30px;
			height: 30px;
		}
	}
</style>
