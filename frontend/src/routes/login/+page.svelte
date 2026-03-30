<script>
	import { _ } from 'svelte-i18n';
	import { authUser } from '$lib/stores/auth';
	import { goto } from '$app/navigation';

	$effect(() => {
		if ($authUser) {
			goto('/');
		}
	});
</script>

<div class="login-page">
	<div class="login-card">
		<h1>{$_('login.h1')}</h1>
		<p>{$_('login.desc')}</p>
		<a href="/api/auth/google/login" class="google-btn">
			<svg aria-hidden="true" width="18" height="18" viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg">
				<path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615Z" fill="#4285F4"/>
				<path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18Z" fill="#34A853"/>
				<path d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.997 8.997 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332Z" fill="#FBBC05"/>
				<path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58Z" fill="#EA4335"/>
			</svg>
			{$_('login.entrarComGoogle')}
		</a>
	</div>
</div>

<style>
	.login-page {
		display: flex;
		justify-content: center;
		align-items: center;
		min-height: 60vh;
	}

	.login-card {
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: 0;
		padding: 3rem;
		text-align: center;
		max-width: 400px;
		width: 100%;
	}

	h1 {
		font-size: 1.5rem;
		margin: 0 0 0.5rem;
		color: var(--text-primary);
	}

	p {
		color: var(--text-secondary);
		margin: 0 0 2rem;
		font-size: 0.938rem;
	}

	.google-btn {
		display: inline-flex;
		align-items: center;
		gap: 0.75rem;
		background: var(--bg-card);
		border: 1.5px solid var(--border);
		border-radius: 0;
		padding: 0.875rem 2rem;
		font-size: 0.875rem;
		font-weight: 600;
		color: var(--text-primary);
		text-decoration: none;
		transition: border-color 0.15s;
	}

	.google-btn:hover {
		border-color: var(--text-primary);
	}
</style>
