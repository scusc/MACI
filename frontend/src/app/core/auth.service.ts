import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap, catchError, of } from 'rxjs';

import { environment } from '../../environments/environment';

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  bio?: string;
  origin_airport?: string;
  avatar_url?: string;
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

  constructor() {
    if (this.getToken()) {
      this.fetchProfile().subscribe({
        error: () => this.logout()
      });
    }
  }

  getToken(): string | null {
    return localStorage.getItem('slice_token');
  }

  register(userData: any): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/register`, userData).pipe(
      tap(res => {
        if (res.access_token || (res.token && res.token.access_token)) {
          const token = res.access_token || res.token.access_token;
          localStorage.setItem('slice_token', token);
          this.fetchProfile().subscribe();
        }
      })
    );
  }

  login(credentials: any): Observable<{token: TokenResponse, user: User}> {
    const payload = {
      email: credentials.email,
      password: credentials.password
    };

    return this.http.post<{token: TokenResponse, user: User}>(`${this.apiUrl}/login`, payload).pipe(
      tap(response => {
        const token = response.token ? response.token.access_token : (response as any).access_token;
        if (token) {
          localStorage.setItem('slice_token', token);
          this.fetchProfile().subscribe();
        }
      })
    );
  }

  loginWithOAuth(provider: 'google' | 'apple', token: string): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/oauth`, { provider, provider_token: token }).pipe(
      tap(res => {
        const jwt = res.token ? res.token.access_token : res.access_token;
        if (jwt) {
          localStorage.setItem('slice_token', jwt);
          this.fetchProfile().subscribe();
        }
      })
    );
  }

  fetchProfile(): Observable<User> {
    return this.http.get<User>(`${this.apiUrl}/me`).pipe(
      tap(user => {
        if (!user.kyc_status) user.kyc_status = 'unverified';
        this.currentUser.set(user);
      })
    );
  }

  updateProfile(updateData: Partial<User>): Observable<User> {
    return this.http.put<User>(`${this.apiUrl}/me`, updateData).pipe(
      tap(updatedUser => {
        this.currentUser.set(updatedUser);
      })
    );
  }

  logout() {
    localStorage.removeItem('slice_token');
    this.currentUser.set(null);
  }

  startKYC(userId: string): Observable<{verification_url: string}> {
    return this.http.post<{verification_url: string}>(`${this.apiUrl}/kyc/start`, {});
  }

  startHostOnboarding(userId: string): Observable<{onboarding_url: string}> {
    return this.http.post<{onboarding_url: string}>(`${this.apiUrl}/host/onboard`, {});
  }
}
