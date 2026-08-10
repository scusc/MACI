import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface TripMember {
  id: string;
  email: string;
  display_name?: string;
  role: 'organizer' | 'member';
  status: 'invited' | 'viewed' | 'committed' | 'paid' | 'declined';
  share_amount: number;
}

export interface Trip {
  id: string;
  title: string;
  destination: string;
  start_date: string;
  end_date: string;
  description: string;
  status: 'draft' | 'collecting' | 'active' | 'cancelled';
  currency: string;
  threshold_pct: number;
  estimated_cost_per_person: number;
  commitment_deadline: string;
  organizer_id: string;
  invite_code: string;
  members: TripMember[];
  media_url?: string;
  weather_temp?: number;
}

export interface Traveler {
  name: string;
  origin: string;
}

export interface TripLeg {
  destination: string;
  arrival_date: string;
  departure_date: string;
}

export interface AIQuoteRequest {
  travelers: Traveler[];
  itinerary: TripLeg[];
  budget_tier: string;
}

export interface FlightDetails {
  airline: string;
  flight_number: string;
  departure_time: string;
  arrival_time: string;
  duration: string;
  cabin_class: string;
}

export interface HotelDetails {
  name: string;
  rating: number;
  address: string;
  image_url?: string;
  amenities: string[];
}

export interface TravelerQuote {
  name: string;
  origin: string;
  flight_route: string;
  individual_cost: number;
  shared_cost: number;
  total_cost: number;
  flight_evidence?: string;
  flights: FlightDetails[]; // Detailed flights array
}

export interface AIQuoteOption {
  id: string;
  title: string;
  shared_cost_per_person: number;
  shared_accommodation_name: string;
  shared_accommodation_total: number;
  hotel_evidence?: string;
  hotel_details?: HotelDetails;
  traveler_quotes: TravelerQuote[];
  reasoning: string;
}

export interface AIQuoteResponse {
  options: AIQuoteOption[];
}

@Injectable({
  providedIn: 'root'
})
export class PoolService {
  private http = inject(HttpClient);
  private apiUrl = `${environment.apiUrl}/trips`;

  getTrips(destination?: string): Observable<Trip[]> {
    let params = new HttpParams();
    if (destination) {
      params = params.set('destination', destination);
    }
    return this.http.get<Trip[]>(this.apiUrl, { params });
  }

  getTrip(tripId: string): Observable<Trip> {
    return this.http.get<Trip>(`${this.apiUrl}/${tripId}`);
  }

  createTrip(tripData: Partial<Trip>): Observable<Trip> {
    return this.http.post<Trip>(this.apiUrl, tripData);
  }

  updateTrip(tripId: string, updateData: Partial<Trip>): Observable<Trip> {
    return this.http.patch<Trip>(`${this.apiUrl}/${tripId}`, updateData);
  }

  deleteTrip(tripId: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${tripId}`);
  }

  joinTrip(tripId: string, memberId: string): Observable<Trip> {
    return this.http.post<Trip>(`${this.apiUrl}/${tripId}/members/${memberId}/commit`, {});
  }

  getAIQuote(params: AIQuoteRequest): Observable<AIQuoteResponse> {
    return this.http.post<AIQuoteResponse>(`${environment.apiUrl}/travel/quote`, params);
  }
}
