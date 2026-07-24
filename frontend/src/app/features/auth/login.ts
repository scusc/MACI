import { Component, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../core/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  templateUrl: './login.html',
  styleUrl: './login.scss',
})
export class Login {
  private fb = inject(FormBuilder);
  private router = inject(Router);
  private authService = inject(AuthService);

  isSubmitting = signal(false);
  errorMessage = signal<string | null>(null);

  loginForm = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(6)]]
  });

  async onSubmit() {
    if (this.loginForm.invalid) {
      this.loginForm.markAllAsTouched();
      return;
    }

    this.isSubmitting.set(true);
    this.errorMessage.set(null);

    const { email, password } = this.loginForm.getRawValue();

    this.authService.login({ email, password }).subscribe({
      next: () => {
        this.isSubmitting.set(false);
        this.router.navigate(['/feed']);
      },
      error: (err) => {
        this.isSubmitting.set(false);
        this.errorMessage.set(err.error?.detail || 'Invalid credentials. Please try again.');
      }
    });
  }

  handleGoogleOAuth() {
    const simulatedGoogleJwt = 'simulated_google_oauth_token_' + Date.now();
    this.authService.loginWithOAuth('google', simulatedGoogleJwt).subscribe({
      next: () => this.router.navigate(['/feed']),
      error: () => {
        alert('Google OAuth: Enter GOOGLE_CLIENT_ID in Azure portal environment variables.');
      }
    });
  }

  handleAppleOAuth() {
    const simulatedAppleJwt = 'simulated_apple_oauth_token_' + Date.now();
    this.authService.loginWithOAuth('apple', simulatedAppleJwt).subscribe({
      next: () => this.router.navigate(['/feed']),
      error: () => {
        alert('Apple Sign-In: Configure APPLE_CLIENT_ID in Azure portal environment variables.');
      }
    });
  }
}
