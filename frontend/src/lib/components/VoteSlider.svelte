<script lang="ts">
	/**
	 * 9-position vote intensity slider.
	 *
	 * Positions map to:
	 *   1 = Contra       (nao, peso 1.00)
	 *   2 =              (nao, peso 0.75)
	 *   3 =              (nao, peso 0.50)
	 *   4 =              (nao, peso 0.25)
	 *   5 = Neutro       (sim, peso 0.00)
	 *   6 =              (sim, peso 0.25)
	 *   7 =              (sim, peso 0.50)
	 *   8 =              (sim, peso 0.75)
	 *   9 = A favor      (sim, peso 1.00)
	 */

	interface Props {
		value?: number | null;
		onvote: (voto: 'sim' | 'nao', peso: number) => void;
		onpular: () => void;
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
		{ pos: 2, voto: 'nao', peso: 0.75 },
		{ pos: 3, voto: 'nao', peso: 0.5 },
		{ pos: 4, voto: 'nao', peso: 0.25 },
		{ pos: 5, voto: 'sim', peso: 0.0, label: 'Neutro' },
		{ pos: 6, voto: 'sim', peso: 0.25 },
		{ pos: 7, voto: 'sim', peso: 0.5 },
		{ pos: 8, voto: 'sim', peso: 0.75 },
		{ pos: 9, voto: 'sim', peso: 1.0, label: 'A favor' },
	];

	const TOOLTIP: Record<number, string> = {
		1: 'Contra (máximo)',
		2: 'Contra (forte)',
		3: 'Contra (moderado)',
		4: 'Contra (leve)',
		5: 'Neutro',
		6: 'A favor (leve)',
		7: 'A favor (moderado)',
		8: 'A favor (forte)',
		9: 'A favor (máximo)',
	};

	let { value = null, onvote, onpular, compact = false }: Props = $props();

	function select(p: Position) {
		onvote(p.voto, p.peso);
	}

	function colorForPos(pos: number): string {
		const colors: Record<number, string> = {
			1: '#dc2626',
			2: '#ef4444',
			3: '#f87171',
			4: '#fca5a5',
			5: '#a3a3a3',
			6: '#86efac',
			7: '#4ade80',
			8: '#22c55e',
			9: '#16a34a',
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
				class:endpoint={p.pos === 1 || p.pos === 5 || p.pos === 9}
				onclick={() => select(p)}
				title={TOOLTIP[p.pos]}
				style:--dot-color={colorForPos(p.pos)}
			>
				<span class="dot"></span>
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
		left: 16px;
		right: 16px;
		height: 4px;
		margin-top: -2px;
		border-radius: 2px;
		overflow: hidden;
		background: var(--border);
	}

	.track-fill {
		position: absolute;
		inset: 0;
		background: linear-gradient(
			to right,
			#dc2626, #ef4444, #f87171, #fca5a5,
			#d4d4d4,
			#86efac, #4ade80, #22c55e, #16a34a
		);
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
		width: 28px;
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

	/* Endpoint dots (Contra, Neutro, A favor) are bigger */
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

	.pular-btn {
		margin-top: 0.35rem;
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
		width: 20px;
	}

	.compact .end-label {
		font-size: 0.6rem;
	}

	.compact .track-bg {
		left: 10px;
		right: 10px;
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
			width: 24px;
		}

		.dot {
			width: 20px;
			height: 20px;
		}

		.pos-btn.endpoint .dot {
			width: 26px;
			height: 26px;
		}
	}
</style>
