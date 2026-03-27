<script lang="ts">
	import { confidenceScore, scoreToDots } from '$lib/utils/score';

	interface Props {
		score: number | null;
		votos_comparados?: number;
		loading?: boolean;
		size?: 'sm' | 'md' | 'lg';
	}

	let { score, votos_comparados = 0, loading = false, size = 'md' }: Props = $props();

	const dots = $derived.by(() => {
		if (score == null) return null;
		const adjusted = confidenceScore(score, votos_comparados);
		return scoreToDots(adjusted);
	});

	const TOTAL_DOTS = 5;

	function dotFill(index: number): 'full' | 'half' | 'empty' {
		if (dots == null) return 'empty';
		const filled = dots / 2; // 0-10 → 0-5 dots
		if (index < Math.floor(filled)) return 'full';
		if (index === Math.floor(filled) && filled % 1 >= 0.5) return 'half';
		return 'empty';
	}

	const dotColor = $derived.by(() => {
		if (dots == null) return '';
		const filledDots = Math.ceil(dots / 2);
		if (filledDots <= 2) return 'var(--accent)';
		if (filledDots <= 4) return 'var(--color-favor)';
		return 'var(--link)';
	});

	const label = $derived.by(() => {
		if (dots == null) return 'Sem dados';
		const adjusted = confidenceScore(score!, votos_comparados);
		return `${Math.round(adjusted)}% de alinhamento (${votos_comparados} votos comparados)`;
	});
</script>

<span class="score-dots {size}" title={label} aria-label={label} style:--dot-color={dotColor}>
	{#if loading}
		<span class="spinner"></span>
	{:else if dots == null}
		<span class="score-na">N/A</span>
	{:else}
		{#each Array(TOTAL_DOTS) as _, i}
			<svg class="dot" viewBox="0 0 16 16" aria-hidden="true">
				{#if dotFill(i) === 'full'}
					<circle cx="8" cy="8" r="7" class="filled" />
				{:else if dotFill(i) === 'half'}
					<defs>
						<clipPath id="half-{i}">
							<rect x="0" y="0" width="8" height="16" />
						</clipPath>
					</defs>
					<circle cx="8" cy="8" r="7" class="empty-bg" />
					<circle cx="8" cy="8" r="7" class="filled" clip-path="url(#half-{i})" />
				{:else}
					<circle cx="8" cy="8" r="7" class="empty-bg" />
				{/if}
			</svg>
		{/each}
	{/if}
</span>

<style>
	.score-dots {
		display: inline-flex;
		align-items: center;
		gap: 3px;
	}

	.dot {
		flex-shrink: 0;
	}

	.score-dots.sm .dot { width: 12px; height: 12px; }
	.score-dots.md .dot { width: 16px; height: 16px; }
	.score-dots.lg .dot { width: 22px; height: 22px; }

	.filled {
		fill: var(--dot-color, var(--color-favor));
	}

	.empty-bg {
		fill: var(--border);
	}

	.score-na {
		color: var(--text-secondary);
		font-style: italic;
		font-size: 0.813rem;
		cursor: help;
	}

	.spinner {
		width: 16px;
		height: 16px;
		border: 2px solid var(--border);
		border-top-color: var(--link);
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}
</style>
