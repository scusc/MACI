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
  public authService = inject(AuthService);
  private router = inject(Router);
  private toastService = inject(ToastService);

  trips = signal<Trip[]>([]);
  currentIndex = signal(0);
  isLoading = signal(false);

  // Filter signal
  searchDestination = signal('');

  // Modal signals
  showCreateModal = signal(false);
  isSearchingTravel = signal(false);
  travelSearchResult = signal<TravelSearchResult | null>(null);

  // Delete confirmation
  tripToDelete = signal<string | null>(null);

  // New post form fields
  postTitle = signal('');
  postOrigin = signal('NYC');
  postDestination = signal('Bali');
  postStartDate = signal('2026-09-01');
  postEndDate = signal('2026-09-07');
  postDescription = signal('');
  postCost = signal(1200);

  selectedFlight = signal<FlightOption | null>(null);
  selectedHotel = signal<HotelOption | null>(null);

  ngOnInit() {
    this.loadFeed();
  }

  loadFeed() {
    this.isLoading.set(true);
    this.poolService.getTrips(this.searchDestination()).subscribe({
      next: (data) => {
        this.trips.set(data || []);
        this.currentIndex.set(0);
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

  currentTrip = computed(() => {
    const list = this.trips();
    const idx = this.currentIndex();
    return idx < list.length ? list[idx] : null;
  });

  isEmpty = computed(() => this.currentTrip() === null);

  nextCard() {
    if (!this.isEmpty()) {
      this.currentIndex.update(i => i + 1);
    }
  }

  prevCard() {
    if (this.currentIndex() > 0) {
      this.currentIndex.update(i => i - 1);
    }
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

    this.poolService.createTrip(payload).subscribe({
      next: (newTrip) => {
        this.closeCreateModal();
        this.loadFeed();
        this.toastService.success('Travel pool published successfully.');
      },
      error: (err) => {
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
