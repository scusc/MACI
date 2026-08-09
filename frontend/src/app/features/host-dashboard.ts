import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuthService } from '../core/auth.service';
import { ToastService } from '../core/toast.service';

@Component({
  selector: 'app-host-dashboard',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './host-dashboard.html',
  styleUrl: './host-dashboard.scss',
})
export class HostDashboard {
  private authService = inject(AuthService);
  private toastService = inject(ToastService);
  
  currentUser = this.authService.currentUser;

  startOnboarding() {
    const user = this.currentUser();
    if (user) {
      this.toastService.info('Redirecting to Stripe Connect onboarding...');
      this.authService.startHostOnboarding(user.id).subscribe({
        next: (res) => {
          if (res.onboarding_url) {
            window.location.href = res.onboarding_url;
          }
        },
        error: (err) => {
          this.toastService.error(err.error?.detail || 'Failed to initialize Stripe Connect onboarding.');
        }
      });
    } else {
      this.toastService.warning('Please sign in to access host dashboard.');
    }
  }
}
