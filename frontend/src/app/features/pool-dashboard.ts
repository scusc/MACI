import { Component, signal, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { PoolService, Trip, AIQuoteResponse } from '../core/pool.service';
import { AuthService } from '../core/auth.service';
import { ToastService } from '../core/toast.service';

@Component({
  selector: 'app-pool-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule],
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

  // --- Create Pool UI ---
  showCreateModal = signal(false);
  isQuoting = signal(false);
  aiQuoteResult = signal<AIQuoteResponse | null>(null);

  poolTitle = signal('');
  poolOrigin = signal('');
  poolDestination = signal('');
  poolStartDate = signal('');
  poolEndDate = signal('');
  poolGroupSize = signal(2);
  poolBudgetTier = signal('balanced');
  poolDescription = signal('');
  poolEstimatedCost = signal<number | null>(null);

  openCreateModal() {
    this.showCreateModal.set(true);
  }

  closeCreateModal() {
    this.showCreateModal.set(false);
    this.aiQuoteResult.set(null);
  }

  goToArchitect() {
    this.router.navigate(['/architect']);
  }

  createPool() {
    if (!this.poolTitle() || !this.poolDestination() || !this.poolEstimatedCost()) {
      this.toastService.error("Please fill required fields.");
      return;
    }

    this.poolService.createTrip({
      title: this.poolTitle(),
      destination: this.poolDestination(),
      start_date: this.poolStartDate() + 'T00:00:00Z',
      end_date: this.poolEndDate() + 'T00:00:00Z',
      description: this.poolDescription(),
      estimated_cost_per_person: this.poolEstimatedCost()!
    }).subscribe({
      next: () => {
        this.toastService.success('Travel pool created!');
        this.closeCreateModal();
        this.loadPools();
      },
      error: (err) => {
        this.toastService.error(err.error?.detail || 'Failed to create pool.');
      }
    });
  }
}
