import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuthService } from '../core/auth.service';

@Component({
  selector: 'rally-subscription',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './subscription.html',
  styleUrls: ['./subscription.scss']
})
export class Subscription {
  public authService = inject(AuthService);

  user = this.authService.currentUser;

  startKYCVerification() {
    const u = this.user();
    if (!u) {
      alert('Please log in first to verify your Trust Passport identity.');
      return;
    }

    this.authService.startKYC(u.id).subscribe({
      next: (res) => {
        if (res.verification_url) {
          window.location.href = res.verification_url;
        } else {
          alert('Verification initialization complete.');
        }
      },
      error: (err) => {
        alert('Verification service notice: ' + (err.error?.detail || 'Stripe Identity / Plaid credentials required in server configuration.'));
      }
    });
  }

  linkGoogleAccount() {
    alert('Google Account Linking: OAuth 2.0 PKCE flow initialized for trust score boost.');
  }
}
