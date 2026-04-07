import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

/** Prevents authenticated users from accessing public-only pages (login, signup). */
export const publicGuard: CanActivateFn = () => {
  const authService = inject(AuthService);
  if (authService.isAuthenticated()) {
    return inject(Router).createUrlTree(['/home']);
  }
  return true;
};
