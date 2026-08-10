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

export interface AIQuoteRequest {
  origin: string;
  destination: string;
  outbound_date: string;
  return_date: string;
  group_size: number;
  budget_tier: string;
}

export interface EvidenceLink {
  label: string;
  url: string;
}

export interface AIQuoteResponse {
  estimated_cost: number;
  reasoning: string;
  evidence_links: EvidenceLink[];
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
