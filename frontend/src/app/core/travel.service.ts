import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface FlightOption {
  id: string;
  airline: string;
  flight_number: string;
  departure_airport: string;
  arrival_airport: string;
  departure_time: string;
  arrival_time: string;
  duration: string;
  price_usd: number;
  cabin_class: string;
  available_seats: number;
}

export interface HotelOption {
  id: string;
  name: string;
  rating: number;
  address: string;
  price_per_night_usd: number;
  amenities: string[];
  image_url: string;
}

export interface DestinationWeather {
  destination: string;
  temp_celsius: number;
  condition: string;
  humidity_pct: number;
  wind_speed_kmh: number;
}

export interface TravelSearchResult {
  origin: string;
  destination: string;
  latitude: number;
  longitude: number;
  weather?: DestinationWeather;
  flights: FlightOption[];
  hotels: HotelOption[];
  ai_summary: string;
}

@Injectable({
  providedIn: 'root'
})
export class TravelService {
  private http = inject(HttpClient);
  private apiUrl = `${environment.apiUrl}/travel`;

  searchTravel(origin: string, destination: string, departureDate?: string, returnDate?: string, passengers: number = 1): Observable<TravelSearchResult> {
    let params = new HttpParams()
      .set('origin', origin)
      .set('destination', destination)
      .set('passengers', passengers.toString());
    
    if (departureDate) params = params.set('departure_date', departureDate);
    if (returnDate) params = params.set('return_date', returnDate);

    return this.http.get<TravelSearchResult>(`${this.apiUrl}/search`, { params });
  }

  generateAIItinerary(destination: string, days: number = 5, budget: string = 'medium', vibe: string = 'balanced'): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/ai-itinerary`, {
      destination,
      days,
      budget,
      travel_vibe: vibe
    });
  }
}
