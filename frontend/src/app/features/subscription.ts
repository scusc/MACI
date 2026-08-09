import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { AuthService } from '../core/auth.service';
import { ToastService } from '../core/toast.service';

@Component({
  selector: 'app-subscription',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './subscription.html',
  styleUrl: './subscription.scss',
})
export class Subscription {
  public authService = inject(AuthService);
  private toastService = inject(ToastService);
  
  user = this.authService.currentUser;

  startKYC() {
    const u = this.user();
    if (!u) {
      this.toastService.info('Please sign in to verify your identity.');
      return;
    }
    
    this.toastService.info('Redirecting to Stripe Identity verification...');
    
    this.authService.startKYC(u.id).subscribe({
      next: (res) => {
        if (res.verification_url) {
          window.location.href = res.verification_url;
        }
      },
      error: (err) => {
        this.toastService.error(err.error?.detail || 'Failed to initialize verification. Please try again later.');
      }
    });
  }
}
