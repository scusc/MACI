import { Component, signal, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { PoolService, Trip } from '../core/pool.service';
import { AuthService } from '../core/auth.service';

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
      }
    });
  }

  deletePool(tripId: string) {
    if (confirm('Delete this travel pool?')) {
      this.poolService.deleteTrip(tripId).subscribe({
        next: () => {
          this.loadPools();
          alert('Pool deleted.');
        },
        error: (err) => alert(err.error?.detail || 'Could not delete pool.')
      });
    }
  }

  openChat(tripId: string) {
    this.router.navigate(['/chat', tripId]);
  }
}
