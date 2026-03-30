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

	import { _ } from 'svelte-i18n';
	import { colorForPos } from '$lib/constants';

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
	}

	const POSITIONS: Position[] = [
		{ pos: 1, voto: 'nao', peso: 1.0 },
		{ pos: 2, voto: 'nao', peso: 0.5 },
		{ pos: 3, voto: 'sim', peso: 0.0 },
		{ pos: 4, voto: 'sim', peso: 0.5 },
		{ pos: 5, voto: 'sim', peso: 1.0 },
	];

	const TOOLTIP_KEYS: Record<number, string> = {
		1: 'slider.contraTooltip',
		2: 'slider.contraLeveTooltip',
		3: 'slider.neutroTooltip',
		4: 'slider.aFavorLeveTooltip',
		5: 'slider.aFavorTooltip',
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

	function handleKeydown(e: KeyboardEvent, p: Position) {
		const idx = POSITIONS.findIndex((pos) => pos.pos === p.pos);
		if (e.key === 'ArrowLeft' && idx > 0) {
			e.preventDefault();
			const prev = POSITIONS[idx - 1];
			handleClick(prev);
			const sibling = (e.currentTarget as HTMLElement)?.previousElementSibling as HTMLElement | null;
			sibling?.focus();
		} else if (e.key === 'ArrowRight' && idx < POSITIONS.length - 1) {
			e.preventDefault();
			const next = POSITIONS[idx + 1];
			handleClick(next);
			const sibling = (e.currentTarget as HTMLElement)?.nextElementSibling as HTMLElement | null;
			sibling?.focus();
		}
	}
</script>

<div class="vote-slider" class:compact>
	<div class="labels-row">
		<span class="end-label left">{$_('slider.contra')}</span>
		<span class="end-label center">{$_('slider.neutro')}</span>
		<span class="end-label right">{$_('slider.aFavor')}</span>
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
				onkeydown={(e) => handleKeydown(e, p)}
				title={$_(TOOLTIP_KEYS[p.pos])}
				aria-label={$_(TOOLTIP_KEYS[p.pos])}
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

	.end-label.left { color: var(--color-contra); }
	.end-label.center { color: var(--color-neutro-dark); }
	.end-label.right { color: var(--color-favor); }

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
		width: 18px;
		height: 18px;
		border-radius: 50%;
		border: 2.5px solid var(--dot-color, var(--border));
		background: var(--bg-card);
		transition: all 0.15s ease;
		flex-shrink: 0;
		will-change: transform;
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
		width: 36px;
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
