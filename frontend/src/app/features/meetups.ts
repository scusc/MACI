import { Component, signal, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { environment } from '../../environments/environment';
import { AuthService } from '../core/auth.service';
import { ToastService } from '../core/toast.service';

export interface Meetup {
  id: string;
  title: string;
  description: string;
  latitude: number;
  longitude: number;
  start_time: string;
  escrow_amount_cents: number;
  check_in_pin?: string;
}

@Component({
  selector: 'app-meetups',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './meetups.html',
  styleUrl: './meetups.scss',
})
export class Meetups implements OnInit {
  private http = inject(HttpClient);
  public authService = inject(AuthService);
  private router = inject(Router);
  private toastService = inject(ToastService);

  meetups = signal<Meetup[]>([]);
  isLoading = signal(false);

  // Modal create
  showCreateModal = signal(false);
  meetupTitle = signal('');
  meetupDescription = signal('');
  meetupLocationName = signal('Seminyak Beach, Bali');
  meetupLatitude = signal(-8.6913);
  meetupLongitude = signal(115.1682);
  meetupEscrowDollars = signal(10);
  meetupStartTime = signal('2026-08-01T17:00');

  // Check-in modal
  showCheckInModal = signal(false);
  selectedMeetup = signal<Meetup | null>(null);
  inputPin = signal('');
  qrPayload = signal('');
  isLoadingQr = signal(false);

  ngOnInit() {
    this.loadMeetups();
  }

  loadMeetups() {
    this.isLoading.set(true);
    this.http.get<Meetup[]>(`${environment.apiUrl}/meetups/all`).subscribe({
      next: (data) => {
        this.meetups.set(data || []);
        this.isLoading.set(false);
      },
      error: () => {
        this.toastService.error('Failed to load meetups.');
        this.isLoading.set(false);
      }
    });
  }

  openCreateModal() {
    if (!this.authService.getToken()) {
      this.toastService.info('Please sign in to create a meetup.');
      this.router.navigate(['/login']);
      return;
    }
    this.showCreateModal.set(true);
  }

  closeCreateModal() {
    this.showCreateModal.set(false);
  }

  searchLocationCoords() {
    if (!this.meetupLocationName()) return;
    this.http.get<any[]>('https://nominatim.openstreetmap.org/search', {
      params: { q: this.meetupLocationName(), format: 'json', limit: 1 }
    }).subscribe({
      next: (res) => {
        if (res && res.length > 0) {
          this.meetupLatitude.set(parseFloat(res[0].lat));
          this.meetupLongitude.set(parseFloat(res[0].lon));
          this.toastService.success(`Location verified: ${res[0].display_name.split(',')[0]}`);
        } else {
          this.toastService.warning('Location not found. Please try a different search term.');
        }
      },
      error: () => {
        this.toastService.error('Failed to search location.');
      }
    });
  }

  createMeetup() {
    if (!this.meetupTitle()) {
      this.toastService.warning('Meetup title is required.');
      return;
    }
    const currentUser = this.authService.currentUser();
    if (!currentUser) return;

    const payload = {
      title: this.meetupTitle(),
      description: this.meetupDescription() || 'Local micro-commitment meetup.',
      latitude: this.meetupLatitude(),
      longitude: this.meetupLongitude(),
      start_time: new Date(this.meetupStartTime()).toISOString(),
      escrow_amount_cents: this.meetupEscrowDollars() * 100
    };

    this.http.post<Meetup>(`${environment.apiUrl}/meetups/?host_id=${currentUser.id}`, payload).subscribe({
      next: () => {
        this.closeCreateModal();
        this.loadMeetups();
        this.toastService.success('Micro-meetup created successfully.');
      },
      error: (err) => {
        this.toastService.error(err.error?.detail || 'Identity verification required to create meetups.');
      }
    });
  }

  openCheckIn(m: Meetup) {
    if (!this.authService.getToken()) {
      this.toastService.info('Please sign in to check in.');
      this.router.navigate(['/login']);
      return;
    }
    
    this.selectedMeetup.set(m);
    this.showCheckInModal.set(true);
    this.inputPin.set('');
    this.isLoadingQr.set(true);
    
    const userId = this.authService.currentUser()?.id;
    if (!userId) return;

    // Fetch QR Code payload
    this.http.get<{qr_payload: string}>(`${environment.apiUrl}/meetups/${m.id}/qr-code`, {
      headers: { 'x-user-id': userId }
    }).subscribe({
      next: (res) => {
        this.qrPayload.set(res.qr_payload);
        this.isLoadingQr.set(false);
      },
      error: () => {
        this.toastService.error('Failed to load check-in QR code.');
        this.isLoadingQr.set(false);
      }
    });
  }

  closeCheckIn() {
    this.showCheckInModal.set(false);
    this.selectedMeetup.set(null);
  }

  submitPinCheckIn() {
    const m = this.selectedMeetup();
    const currentUser = this.authService.currentUser();
    if (!m || !currentUser) return;

    if (!this.inputPin()) {
      this.toastService.warning('Please enter the 4-digit PIN.');
      return;
    }

    this.http.post(`${environment.apiUrl}/meetups/${m.id}/check-in`, null, {
      params: { user_id: currentUser.id, pin: this.inputPin() }
    }).subscribe({
      next: () => {
        this.toastService.success('Physical check-in verified! Escrow released.');
        this.closeCheckIn();
      },
      error: (err) => {
        this.toastService.error(err.error?.detail || 'Invalid Host PIN.');
      }
    });
  }
}
