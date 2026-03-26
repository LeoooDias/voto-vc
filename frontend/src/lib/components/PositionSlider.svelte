<script lang="ts">
	/**
	 * 5-position stance slider for thematic positions.
	 *
	 * Positions:
	 *   1 = Contra       (nao, peso 1.0)
	 *   2 = Contra leve  (nao, peso 0.5)
	 *   3 = Neutro       (sim, peso 0.0)
	 *   4 = A favor leve (sim, peso 0.5)
	 *   5 = A favor      (sim, peso 1.0)
	 */

	import { colorForPos } from '$lib/constants';

	interface Props {
		value?: number | null;
		onselect?: (pos: number) => void;
	}

	interface Position {
		pos: number;
		label: string;
	}

	const POSITIONS: Position[] = [
		{ pos: 1, label: 'Contra' },
		{ pos: 2, label: 'Contra leve' },
		{ pos: 3, label: 'Neutro' },
		{ pos: 4, label: 'A favor leve' },
		{ pos: 5, label: 'A favor' }
	];

	let { value = null, onselect }: Props = $props();

	function handleClick(pos: number) {
		onselect?.(pos);
	}

	function handleKeydown(e: KeyboardEvent, pos: number) {
		const idx = POSITIONS.findIndex((p) => p.pos === pos);
		if (e.key === 'ArrowLeft' && idx > 0) {
			e.preventDefault();
			handleClick(POSITIONS[idx - 1].pos);
			const sibling = (e.currentTarget as HTMLElement)?.previousElementSibling as HTMLElement | null;
			sibling?.focus();
		} else if (e.key === 'ArrowRight' && idx < POSITIONS.length - 1) {
			e.preventDefault();
			handleClick(POSITIONS[idx + 1].pos);
			const sibling = (e.currentTarget as HTMLElement)?.nextElementSibling as HTMLElement | null;
			sibling?.focus();
		}
	}
</script>

<div class="position-slider">
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
				onclick={() => handleClick(p.pos)}
				onkeydown={(e) => handleKeydown(e, p.pos)}
				title={p.label}
				aria-label={p.label}
				style:--dot-color={colorForPos(p.pos)}
			>
				<span class="dot"></span>
			</button>
		{/each}
	</div>
</div>

<style>
	.position-slider {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.3rem;
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

	.end-label.left {
		color: var(--color-contra);
	}
	.end-label.center {
		color: var(--color-neutro-dark);
	}
	.end-label.right {
		color: var(--color-favor);
	}

	.slider-row {
		display: flex;
		width: 100%;
		justify-content: space-between;
		position: relative;
		padding: 0 8px;
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
		background: linear-gradient(to right, var(--color-contra), var(--color-contra-leve), #d4d4d4, var(--color-favor-leve), var(--color-favor));
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
		width: 44px;
	}

	.dot {
		width: 22px;
		height: 22px;
		border-radius: 50%;
		border: 2.5px solid var(--dot-color, var(--border));
		background: var(--bg-card);
		transition: all 0.15s ease;
		flex-shrink: 0;
		will-change: transform;
	}

	.pos-btn.endpoint .dot {
		width: 28px;
		height: 28px;
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

	@media (max-width: 480px) {
		.pos-btn {
			width: 48px;
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
