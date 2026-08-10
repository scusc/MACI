import { Component, signal, computed, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { PoolService, Trip } from '../core/pool.service';
import { TravelService, TravelSearchResult, FlightOption, HotelOption } from '../core/travel.service';
import { AuthService } from '../core/auth.service';
import { ToastService } from '../core/toast.service';

@Component({
  selector: 'app-swipe-feed',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './swipe-feed.html',
  styleUrl: './swipe-feed.scss',
})
export class SwipeFeed implements OnInit {
  private poolService = inject(PoolService);
  private travelService = inject(TravelService);
  private authService = inject(AuthService);
  private router = inject(Router);
  private toastService = inject(ToastService);

  currentUser = this.authService.currentUser;

  trips = signal<Trip[]>([]);
  isLoading = signal(false);

  // Filter signals
  searchDestination = signal('');
  searchMaxBudget = signal<number | null>(null);
  searchStartDate = signal('');
  searchEndDate = signal('');
  showFilters = signal(false);

  filteredTrips = computed(() => {
    let list = this.trips();
    
    // The destination filter is mostly handled by the backend, but we can do a local check too just in case
    if (this.searchDestination()) {
      const term = this.searchDestination().toLowerCase();
      list = list.filter(t => t.destination.toLowerCase().includes(term));
    }

    if (this.searchMaxBudget()) {
      list = list.filter(t => t.estimated_cost_per_person <= (this.searchMaxBudget() as number));
    }

    if (this.searchStartDate()) {
      const filterStart = new Date(this.searchStartDate()).getTime();
      list = list.filter(t => new Date(t.start_date).getTime() >= filterStart);
    }

    if (this.searchEndDate()) {
      const filterEnd = new Date(this.searchEndDate()).getTime();
      list = list.filter(t => new Date(t.end_date).getTime() <= filterEnd);
    }

    return list;
  });

  // Modal signals
  showCreateModal = signal(false);
  isSearchingTravel = signal(false);
  travelSearchResult = signal<TravelSearchResult | null>(null);

  isQuoting = signal(false);
  aiQuoteResult = signal<any>(null);
  poolGroupSize = signal(4);
  poolBudgetTier = signal('balanced');

  // Delete confirmation
  tripToDelete = signal<string | null>(null);

  // New post form fields
  postTitle = signal('');
  postOrigin = signal('');
  postDestination = signal('');
  postStartDate = signal('');
  postEndDate = signal('');
  postDescription = signal('');
  postCost = signal(0);

  selectedFlight = signal<FlightOption | null>(null);
  selectedHotel = signal<HotelOption | null>(null);
  isPublishing = signal(false);

  ngOnInit() {
    this.loadFeed();
  }

  loadFeed() {
    this.isLoading.set(true);
    this.poolService.getTrips(this.searchDestination()).subscribe({
      next: (data) => {
        this.trips.set(data || []);
        this.isLoading.set(false);
      },
      error: () => {
        this.toastService.error('Failed to load travel pools.');
        this.isLoading.set(false);
      }
    });
  }

  onSearch() {
    this.loadFeed();
  }

  isEmpty = computed(() => this.filteredTrips().length === 0);

  toggleFilters() {
    this.showFilters.update(v => !v);
  }

  openCreateModal() {
    if (!this.authService.getToken()) {
      this.toastService.info('Please sign in to create a travel pool.');
      this.router.navigate(['/login']);
      return;
    }
    this.showCreateModal.set(true);
  }

  closeCreateModal() {
    this.showCreateModal.set(false);
    this.travelSearchResult.set(null);
  }

  performLiveTravelSearch() {
    if (!this.postOrigin() || !this.postDestination()) return;
    this.isSearchingTravel.set(true);

    this.travelService.searchTravel(
      this.postOrigin(),
      this.postDestination(),
      this.postStartDate(),
      this.postEndDate(),
      1
    ).subscribe({
      next: (res) => {
        this.travelSearchResult.set(res);
        this.isSearchingTravel.set(false);
        if (res.flights && res.flights.length > 0) {
          this.selectedFlight.set(res.flights[0]);
        }
        if (res.hotels && res.hotels.length > 0) {
          this.selectedHotel.set(res.hotels[0]);
          this.postCost.set(Math.round(res.flights[0].price_usd + res.hotels[0].price_per_night_usd * 5));
        }
        this.toastService.success('Live travel options retrieved successfully.');
      },
      error: (err) => {
        this.isSearchingTravel.set(false);
        this.toastService.error('Failed to retrieve live travel options.');
      }
    });
  }

  goToArchitect() {
    this.router.navigate(['/architect']);
  }

  submitNewPost() {
    if (!this.postTitle() || !this.postDestination()) {
      this.toastService.warning('Please fill in all required fields.');
      return;
    }

    const payload: Partial<Trip> = {
      title: this.postTitle(),
      destination: this.postDestination(),
      start_date: new Date(this.postStartDate()).toISOString(),
      end_date: new Date(this.postEndDate()).toISOString(),
      description: this.postDescription() || `Group trip to ${this.postDestination()}.`,
      estimated_cost_per_person: this.postCost(),
      threshold_pct: 60,
      currency: 'USD'
    };

    this.isPublishing.set(true);

    this.poolService.createTrip(payload).subscribe({
      next: (newTrip) => {
        this.isPublishing.set(false);
        this.closeCreateModal();
        this.loadFeed();
        this.toastService.success('Travel pool published successfully.');
      },
      error: (err) => {
        this.isPublishing.set(false);
        this.toastService.error(err.error?.detail || 'Identity verification required to create pools.');
      }
    });
  }

  confirmDelete(tripId: string) {
    this.tripToDelete.set(tripId);
  }

  cancelDelete() {
    this.tripToDelete.set(null);
  }

  executeDelete() {
    const tripId = this.tripToDelete();
    if (!tripId) return;

    this.poolService.deleteTrip(tripId).subscribe({
      next: () => {
        this.tripToDelete.set(null);
        this.loadFeed();
        this.toastService.info('Travel pool deleted.');
      },
      error: (err) => {
        this.tripToDelete.set(null);
        this.toastService.error(err.error?.detail || 'Could not delete post.');
      }
    });
  }

  joinPool(trip: Trip) {
    if (!this.authService.getToken()) {
      this.toastService.info('Please sign in to join pools.');
      this.router.navigate(['/login']);
      return;
    }
    const currentUser = this.authService.currentUser();
    if (!currentUser) return;

    this.poolService.joinTrip(trip.id, currentUser.id).subscribe({
      next: () => {
        this.toastService.success('Successfully joined the travel pool.');
        this.loadFeed();
      },
      error: (err) => {
        this.toastService.error(err.error?.detail || 'Identity verification (KYC) required to commit to pools.');
      }
    });
  }

  openChat(tripId: string) {
    this.router.navigate(['/chat', tripId]);
  }
}
