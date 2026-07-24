import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';
import { AuthService } from '../core/auth.service';

@Component({
  selector: 'rally-psychometric-quiz',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './psychometric-quiz.html',
  styleUrls: ['./psychometric-quiz.scss']
})
export class PsychometricQuiz {
  private http = inject(HttpClient);
  private router = inject(Router);
  public authService = inject(AuthService);

  step = 1;

  socialBattery = 5;
  pacing = 5;
  budgetTolerance = 5;
  spontaneity = 5;
  conflictStyle = 5;

  isSubmitting = false;

  nextStep() {
    if (this.step < 5) {
      this.step++;
    } else {
      this.submitQuiz();
    }
  }

  prevStep() {
    if (this.step > 1) {
      this.step--;
    }
  }

  submitQuiz() {
    this.isSubmitting = true;

    const payload = {
      social_battery: this.socialBattery,
      pacing: this.pacing,
      budget_tolerance: this.budgetTolerance,
      spontaneity: this.spontaneity,
      conflict_style: this.conflictStyle
    };

    this.http.post(`${environment.apiUrl}/matching/calculate`, payload).subscribe({
      next: (res: any) => {
        this.isSubmitting = false;
        // Refresh profile if logged in
        if (this.authService.getToken()) {
          this.authService.fetchProfile().subscribe();
        }
        alert('🎉 AI Vibe Vector Calibrated! Your psychometric profile has been updated.');
        this.router.navigate(['/feed']);
      },
      error: () => {
        this.isSubmitting = false;
        this.router.navigate(['/feed']);
      }
    });
  }
}
