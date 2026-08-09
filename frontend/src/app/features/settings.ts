import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService, User } from '../core/auth.service';
import { ToastService } from '../core/toast.service';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './settings.html',
  styleUrl: './settings.scss',
})
export class Settings implements OnInit {
  private authService = inject(AuthService);
  private toastService = inject(ToastService);

  user = this.authService.currentUser;
  
  firstName = signal('');
  lastName = signal('');
  bio = signal('');
  originAirport = signal('');
  avatarUrl = signal('');

  isSaving = signal(false);

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
    if (!this.firstName() || !this.lastName()) {
      this.toastService.warning('First and last name are required.');
      return;
    }

    this.isSaving.set(true);

    this.authService.updateProfile({
      first_name: this.firstName(),
      last_name: this.lastName(),
      bio: this.bio(),
      origin_airport: this.originAirport(),
      avatar_url: this.avatarUrl()
    }).subscribe({
      next: () => {
        this.isSaving.set(false);
        this.toastService.success('Profile updated successfully.');
      },
      error: (err) => {
        this.isSaving.set(false);
        this.toastService.error(err.error?.detail || 'Failed to update profile.');
      }
    });
  }

  wipeMockData() {
    this.toastService.info('Wiping mock data...');
    // I will just use fetch to keep it simple since we have the token
    const token = this.authService.getToken();
    fetch('/api/v1/trips/admin/wipe-mock-data', {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }).then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
          this.toastService.success('Mock data wiped successfully.');
        } else {
          this.toastService.error('Failed to wipe mock data.');
        }
      }).catch(() => {
        this.toastService.error('Error wiping mock data.');
      });
  }
}
