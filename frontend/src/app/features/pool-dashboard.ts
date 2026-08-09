import { Component, signal, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { PoolService, Trip } from '../core/pool.service';
import { AuthService } from '../core/auth.service';
import { ToastService } from '../core/toast.service';

@Component({
  selector: 'app-pool-dashboard',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './pool-dashboard.html',
  styleUrl: './pool-dashboard.scss',
})
export class PoolDashboard implements OnInit {
  private poolService = inject(PoolService);
  public authService = inject(AuthService);
  private router = inject(Router);
  private toastService = inject(ToastService);

  trips = signal<Trip[]>([]);
  isLoading = signal(true);
  currentUser = this.authService.currentUser;

  ngOnInit() {
    this.loadPools();
  }

  loadPools() {
    this.isLoading.set(true);
    this.poolService.getTrips().subscribe({
      next: (data) => {
        this.trips.set(data || []);
        this.isLoading.set(false);
      },
      error: () => {
        this.isLoading.set(false);
        this.toastService.error('Failed to load pools.');
      }
    });
  }

  deletePool(tripId: string) {
    if (window.confirm('Are you sure you want to delete this travel pool?')) {
      this.poolService.deleteTrip(tripId).subscribe({
        next: () => {
          this.loadPools();
          this.toastService.info('Travel pool deleted.');
        },
        error: (err) => this.toastService.error(err.error?.detail || 'Could not delete pool.')
      });
    }
  }

  openChat(tripId: string) {
    this.router.navigate(['/chat', tripId]);
  }
}
