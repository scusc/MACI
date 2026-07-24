import { Component, signal, computed, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { PoolService, Trip } from '../core/pool.service';
import { TravelService, TravelSearchResult, FlightOption, HotelOption } from '../core/travel.service';
import { AuthService } from '../core/auth.service';

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

  trips = signal<Trip[]>([]);
  currentIndex = signal(0);
  isLoading = signal(false);

  // Filter signal
  searchDestination = signal('');

  // Modal signals
  showCreateModal = signal(false);
  isSearchingTravel = signal(false);
  travelSearchResult = signal<TravelSearchResult | null>(null);

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
        this.isLoading.set(false);
      },
      error: () => {
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
          this.postCost.set(res.flights[0].price_usd + res.hotels[0].price_per_night_usd * 5);
        }
      },
      error: () => {
        this.isSearchingTravel.set(false);
      }
    });
  }

  submitNewPost() {
    if (!this.postTitle() || !this.postDestination()) return;

    const payload: Partial<Trip> = {
      title: this.postTitle(),
      destination: this.postDestination(),
      start_date: new Date(this.postStartDate()).toISOString(),
      end_date: new Date(this.postEndDate()).toISOString(),
      description: this.postDescription() || `Group trip to ${this.postDestination()} with real API travel option.`,
      estimated_cost_per_person: this.postCost(),
      threshold_pct: 60,
      currency: 'USD'
    };

    this.poolService.createTrip(payload).subscribe({
      next: (newTrip) => {
        this.closeCreateModal();
        this.loadFeed();
        alert('🎉 Post & Pool published successfully with real live travel data!');
      },
      error: (err) => {
        alert('Failed to publish post: ' + (err.error?.detail || 'Identity verification required to create pools.'));
      }
    });
  }

  deletePost(tripId: string) {
    if (confirm('Are you sure you want to delete this travel pool post?')) {
      this.poolService.deleteTrip(tripId).subscribe({
        next: () => {
          this.loadFeed();
          alert('Post deleted.');
        },
        error: (err) => {
          alert(err.error?.detail || 'Could not delete post.');
        }
      });
    }
  }

  joinPool(trip: Trip) {
    if (!this.authService.getToken()) {
      this.router.navigate(['/login']);
      return;
    }
    const currentUser = this.authService.currentUser();
    if (!currentUser) return;

    this.poolService.joinTrip(trip.id, currentUser.id).subscribe({
      next: () => {
        alert('✅ You have joined this pool!');
        this.loadFeed();
      },
      error: (err) => {
        alert(err.error?.detail || 'Identity verification (KYC) required to commit to pools.');
      }
    });
  }

  openChat(tripId: string) {
    this.router.navigate(['/chat', tripId]);
  }
}
