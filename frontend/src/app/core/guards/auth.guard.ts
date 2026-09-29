import { inject } from '@angular/core';
import { Router, CanActivateFn, CanMatchFn } from '@angular/router';
import { AuthStore } from '../store/auth.store';

export const authGuard: CanActivateFn = async (route, state) => {
  const authStore = inject(AuthStore);
  const router = inject(Router);

  if (authStore.isAuthenticated()) {
    return true;
  }

  // Attempt silent refresh if state is idle
  if (authStore.status() === 'idle') {
    const isSuccess = await authStore.initSession();
    if (isSuccess) return true;
  }

  router.navigate(['/login'], { queryParams: { returnUrl: state.url } });
  return false;
};

export const guestGuard: CanActivateFn = async (route, state) => {
  const authStore = inject(AuthStore);
  const router = inject(Router);

  if (authStore.isAuthenticated()) {
    router.navigate(['/workspace']);
    return false;
  }

  if (authStore.status() === 'idle') {
    const isSuccess = await authStore.initSession();
    if (isSuccess) {
      router.navigate(['/workspace']);
      return false;
    }
  }

  return true;
};
