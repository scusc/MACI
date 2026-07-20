import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuthService } from '../core/auth.service';

@Component({
  selector: 'app-host-dashboard',
  imports: [CommonModule],
  templateUrl: './host-dashboard.html',
  styleUrl: './host-dashboard.scss',
})
export class HostDashboard {
  private authService = inject(AuthService);
  currentUser = this.authService.currentUser;

  startOnboarding() {
    const user = this.currentUser();
    if (user) {
      this.authService.startHostOnboarding(user.id).subscribe({
        next: (res) => window.location.href = res.onboarding_url,
        error: (err) => alert('Failed to initialize Stripe Connect.')
      });
    }
  }
}
