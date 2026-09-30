import { inject } from '@angular/core';
import { Router, CanActivateFn, CanMatchFn } from '@angular/router';
import { AuthStore } from '../store/auth.store';

/**
 * Validates that a returnUrl is strictly a relative path to prevent open redirect vulnerabilities.
 */

export function sanitizeReturnUrl(url?: string): string {
  if (!url || typeof url !== 'string') return '/workspace';
  const trimmed = url.trim();

  // Must start with '/' and must NOT start with '//' or contain '://'
  if (!trimmed.startsWith('/') || trimmed.startsWith('//') || trimmed.includes('://')) {
    return '/workspace';
  }
  return trimmed;
}

export const authGuard: CanActivateFn & CanMatchFn = async (route, state) => {
  const authStore = inject(AuthStore);
  const router = inject(Router);

  if (authStore.isAuthenticated()) {
    return true;
  }

  // Attempt silent refresh if state is idle
  if (authStore.status() === 'idle') {
    const isSuccess = await authStore.initSession();
    if (isSuccess && authStore.isAuthenticated()) {
      return true;
    }
  }

  const rawUrl = state?.url || (route as any)?.path || '/workspace';
  const returnUrl = sanitizeReturnUrl(rawUrl);

  router.navigate(['/auth/login'], { queryParams: { returnUrl } });
  return false;
};

export const guestGuard: CanActivateFn & CanMatchFn = async (route, state) => {
  const authStore = inject(AuthStore);
  const router = inject(Router);

  if (authStore.isAuthenticated()) {
    router.navigate(['/workspace'], { replaceUrl: true });
    return false;
  }

  if (authStore.status() === 'idle') {
    const isSuccess = await authStore.initSession();
    if (isSuccess && authStore.isAuthenticated()) {
      router.navigate(['/workspace'], { replaceUrl: true });
      return false;
    }
  }

  return true;
};
