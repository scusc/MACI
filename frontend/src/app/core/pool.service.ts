import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Pool {
  id: string;
  asset_id: string;
  host_id: string;
  start_date: string;
  end_date: string;
  funding_deadline: string;
  status: 'funding' | 'locked' | 'confirmed' | 'cancelled';
  require_vibe_check: boolean;
  
  // Synthesized fields for the UI
  assetTitle?: string;
  slicesCommitted?: number;
  totalSlices?: number;
  costPerSlice?: number;
}

@Injectable({
  providedIn: 'root'
})
export class PoolService {
  private http = inject(HttpClient);
  private apiUrl = 'http://localhost:8001/api/v1/pools'; 

  getMyPools(): Observable<Pool[]> {
    return this.http.get<Pool[]>(`${this.apiUrl}/me`);
  }

  joinPool(poolId: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/${poolId}/join`, {});
  }

  cancelCommitment(poolId: string): Observable<any> {
    return this.http.post(`http://localhost:8003/api/v1/escrow/pool/${poolId}/withdraw`, {});
  }
}
