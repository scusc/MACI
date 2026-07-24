import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

@Component({
  selector: 'rally-psychometric-quiz',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './psychometric-quiz.html',
  styleUrls: ['./psychometric-quiz.scss']
})
export class PsychometricQuiz {
  step = 1;

  socialBattery = 5;
  pacing = 5;
  budgetTolerance = 5;
  spontaneity = 5;
  conflictStyle = 5;

  isSubmitting = false;

  constructor(private router: Router) {}

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
    setTimeout(() => {
      this.isSubmitting = false;
      this.router.navigate(['/feed']);
    }, 1200);
  }
}
