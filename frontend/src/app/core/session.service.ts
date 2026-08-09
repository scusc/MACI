import { Injectable, inject, NgZone } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from './auth.service';
import { ToastService } from './toast.service';

@Injectable({
  providedIn: 'root'
})
export class SessionService {
  private authService = inject(AuthService);
  private toastService = inject(ToastService);
  private router = inject(Router);
  private ngZone = inject(NgZone);
  
  private timeoutId: any;
  private readonly TIMEOUT_MS = 15 * 60 * 1000; // 15 minutes

  init() {
    this.resetTimer();
    this.setupEventListeners();
  }

  private setupEventListeners() {
    this.ngZone.runOutsideAngular(() => {
      window.addEventListener('mousemove', () => this.resetTimer());
      window.addEventListener('click', () => this.resetTimer());
      window.addEventListener('keypress', () => this.resetTimer());
      window.addEventListener('scroll', () => this.resetTimer());
    });
  }

  private resetTimer() {
    if (this.authService.getToken() === null) return;

    if (this.timeoutId) {
      clearTimeout(this.timeoutId);
    }
    
    this.ngZone.runOutsideAngular(() => {
      this.timeoutId = setTimeout(() => this.logout(), this.TIMEOUT_MS);
    });
  }

  private logout() {
    this.ngZone.run(() => {
      if (this.authService.getToken() !== null) {
        this.authService.logout();
        this.toastService.warning('You have been logged out due to inactivity.');
        this.router.navigate(['/login']);
      }
    });
  }
}
