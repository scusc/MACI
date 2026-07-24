import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';

import { environment } from '../../environments/environment';

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  is_verified: boolean;
  kyc_status: 'unverified' | 'pending' | 'verified';
  karma_score: number;
}

interface TokenResponse {
  access_token: string;
  token_type: string;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private http = inject(HttpClient);
  
  private apiUrl = `${environment.apiUrl}/auth`; 

  // Global reactive state for the logged-in user
  currentUser = signal<User | null>(null);

  getToken(): string | null {
    return localStorage.getItem('slice_token');
  }

  login(credentials: any): Observable<{token: TokenResponse, user: User}> {
    const payload = {
      email: credentials.email,
      password: credentials.password
    };

    return this.http.post<{token: TokenResponse, user: User}>(`${this.apiUrl}/login`, payload).pipe(
      tap(response => {
        localStorage.setItem('slice_token', response.token.access_token);
        this.fetchProfile().subscribe();
      })
    );
  }

  fetchProfile(): Observable<User> {
    return this.http.get<User>(`${this.apiUrl}/me`).pipe(
      tap(user => {
        // Fallback for mocked local testing
        if (!user.kyc_status) user.kyc_status = 'unverified';
        this.currentUser.set(user);
      })
    );
  }

  logout() {
    localStorage.removeItem('slice_token');
    this.currentUser.set(null);
  }

  startKYC(userId: string): Observable<{verification_url: string}> {
    const headers = { Authorization: `Bearer ${this.getToken()}` };
    return this.http.post<{verification_url: string}>(`${this.apiUrl}/kyc/start`, {}, { headers });
  }

  startHostOnboarding(userId: string): Observable<{onboarding_url: string}> {
    const headers = { Authorization: `Bearer ${this.getToken()}` };
    return this.http.post<{onboarding_url: string}>(`${this.apiUrl}/host/onboard`, {}, { headers });
  }
}
