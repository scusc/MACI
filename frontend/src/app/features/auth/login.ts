import { Component, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../core/auth.service';
import { ToastService } from '../../core/toast.service';

declare const google: any;

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
  private toastService = inject(ToastService);

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
        this.toastService.success('Welcome back! You are now signed in.');
        this.router.navigate(['/feed']);
      },
      error: (err) => {
        this.isSubmitting.set(false);
        this.errorMessage.set(err.error?.detail || 'Invalid credentials. Please check your email and password.');
      }
    });
  }

  handleGoogleOAuth() {
    // Use Google Identity Services (GIS) for real OAuth
    // This requires the Google GIS script loaded in index.html
    try {
      google.accounts.id.initialize({
        client_id: '1043294374752-lumvimthmun0lv7sljjv21hbf31t48n4.apps.googleusercontent.com',
        callback: (response: any) => {
          this.authService.loginWithOAuth('google', response.credential).subscribe({
            next: () => {
              this.toastService.success('Signed in with Google successfully.');
              this.router.navigate(['/feed']);
            },
            error: (err) => {
              this.toastService.error(err.error?.detail || 'Google sign-in failed. Please try again.');
            }
          });
        }
      });
      google.accounts.id.prompt();
    } catch {
      this.toastService.error('Google Sign-In is not available. Please use email login.');
    }
  }
}
