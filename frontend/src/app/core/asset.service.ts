import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';

export interface Asset {
  id: string;
  title: string;
  description: string;
  category: string;
  location: string;
  total_price: number;
  currency: string;
  total_slices: number;
  external_reference_id: string;
  media_urls: string[];
}

@Injectable({
  providedIn: 'root'
})
export class AssetService {
  private http = inject(HttpClient);
  private apiUrl = `${environment.apiUrl}/assets`; 

  searchInventory(query: string, checkIn: string, checkOut: string, category: string): Observable<Asset[]> {
    const payload = {
      query,
      check_in: checkIn,
      check_out: checkOut,
      category,
      adults: 4
    };
    return this.http.post<Asset[]>(`${this.apiUrl}/import-from-serpapi`, payload);
  }

  getAsset(id: string): Observable<Asset> {
    return this.http.get<Asset>(`${this.apiUrl}/${id}`);
  }
}
