import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService, User } from '../core/auth.service';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './settings.html',
  styleUrl: './settings.scss',
})
export class Settings implements OnInit {
  private authService = inject(AuthService);

  user = this.authService.currentUser;
  
  firstName = signal('');
  lastName = signal('');
  bio = signal('');
  originAirport = signal('');
  avatarUrl = signal('');

  isSaving = signal(false);
  successMsg = signal('');
  errorMsg = signal('');

  ngOnInit() {
    const u = this.user();
    if (u) {
      this.firstName.set(u.first_name || '');
      this.lastName.set(u.last_name || '');
      this.bio.set(u.bio || '');
      this.originAirport.set(u.origin_airport || '');
      this.avatarUrl.set(u.avatar_url || '');
    }
  }

  saveProfile() {
    this.isSaving.set(true);
    this.successMsg.set('');
    this.errorMsg.set('');

    this.authService.updateProfile({
      first_name: this.firstName(),
      last_name: this.lastName(),
      bio: this.bio(),
      origin_airport: this.originAirport(),
      avatar_url: this.avatarUrl()
    }).subscribe({
      next: () => {
        this.isSaving.set(false);
        this.successMsg.set('Profile updated successfully!');
      },
      error: (err) => {
        this.isSaving.set(false);
        this.errorMsg.set(err.error?.detail || 'Failed to update profile.');
      }
    });
  }

  startVerification() {
    const u = this.user();
    if (!u) return;
    this.authService.startKYC(u.id).subscribe({
      next: (res) => {
        if (res.verification_url) {
          window.location.href = res.verification_url;
        }
      },
      error: (err) => {
        alert('Stripe/Plaid verification initialization: ' + (err.error?.detail || 'Please check environment keys.'));
      }
    });
  }
}
