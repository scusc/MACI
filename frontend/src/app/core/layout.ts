import { Component, inject, OnInit, OnDestroy, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, RouterLinkActive, Router } from '@angular/router';
import { AuthService } from './auth.service';
import { ToastService } from './toast.service';
import { Footer } from './footer';
import { ToastContainer } from './toast.component';

@Component({
  selector: 'app-layout',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive, Footer, ToastContainer],
  templateUrl: './layout.html',
  styleUrl: './layout.scss',
})
export class Layout implements OnInit, OnDestroy {
  authService = inject(AuthService);
  private toastService = inject(ToastService);
  private router = inject(Router);

  currentUser = this.authService.currentUser;
  mobileMenuOpen = false;

  private tokenCheckInterval: any;
  private idleTimeout: any;
  private idleLimitMs = 15 * 60 * 1000; // 15 minutes

  ngOnInit() {
    // Check token expiry every 30 seconds
    this.tokenCheckInterval = setInterval(() => {
      this.checkTokenExpiry();
    }, 30000);

    this.resetIdleTimer();
  }

  ngOnDestroy() {
    if (this.tokenCheckInterval) clearInterval(this.tokenCheckInterval);
    if (this.idleTimeout) clearTimeout(this.idleTimeout);
  }

  @HostListener('document:mousemove')
  @HostListener('document:keydown')
  @HostListener('document:click')
  @HostListener('document:scroll')
  onActivity() {
    this.resetIdleTimer();
  }

  private resetIdleTimer() {
    if (this.idleTimeout) clearTimeout(this.idleTimeout);

    if (this.authService.getToken()) {
      this.idleTimeout = setTimeout(() => {
        this.toastService.warning('Session expired due to inactivity. Please sign in again.');
        this.logout();
      }, this.idleLimitMs);
    }
  }

  private checkTokenExpiry() {
    const token = this.authService.getToken();
    if (!token) return;

    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      const expMs = payload.exp * 1000;
      const now = Date.now();

      if (now >= expMs) {
        this.toastService.warning('Your session has expired. Please sign in again.');
        this.logout();
      } else if (expMs - now < 120000) {
        // Less than 2 minutes remaining
        this.toastService.info('Your session will expire soon. Save your work.');
      }
    } catch {
      // Invalid token format
      this.logout();
    }
  }

  toggleMobileMenu() {
    this.mobileMenuOpen = !this.mobileMenuOpen;
  }

  closeMobileMenu() {
    this.mobileMenuOpen = false;
  }

  logout() {
    this.authService.logout();
    this.router.navigate(['/login']);
  }
}
