import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

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
  private apiUrl = 'http://localhost:8002/api/v1/assets'; 

  searchInventory(query: string, checkIn: string, checkOut: string, category: string): Observable<Asset[]> {
    let params = new HttpParams()
      .set('query', query)
      .set('check_in', checkIn)
      .set('check_out', checkOut);
      
    if (category) {
      params = params.set('category', category);
    }

    return this.http.get<Asset[]>(`${this.apiUrl}/search`, { params });
  }

  getAsset(id: string): Observable<Asset> {
    return this.http.get<Asset>(`${this.apiUrl}/${id}`);
  }
}
