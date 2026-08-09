import { Component, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../core/auth.service';
import { ToastService } from '../core/toast.service';

@Component({
  selector: 'app-psychometric-quiz',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './psychometric-quiz.html',
  styleUrl: './psychometric-quiz.scss',
})
export class PsychometricQuiz {
  private authService = inject(AuthService);
  private router = inject(Router);
  private toastService = inject(ToastService);

  // States: 'intro', 'quiz', 'results'
  currentView = signal<'intro' | 'quiz' | 'results'>('intro');

  step = signal(0);
  isSubmitting = signal(false);
  
  // Archtype result
  archetype = signal<string | null>(null);

  questions = [
    {
      id: 'conflict',
      question: 'Scenario: You arrive at your luxury villa in Bali, but there is a mix-up and one bedroom is a pull-out couch. How do you handle it?',
      context: 'Travel stress is inevitable. We match you with people who have complementary conflict-resolution styles to prevent meltdowns.',
      options: [
        { label: 'Take the couch myself to avoid drama.', value: 10 },
        { label: 'Suggest we rotate who sleeps on the couch.', value: 50 },
        { label: 'Demand the host refunds us so we can book another place.', value: 90 }
      ]
    },
    {
      id: 'budget',
      question: 'How do you typically approach group expenses like dinners and taxis?',
      context: 'Financial friction is the #1 reason group trips fail. We ensure you travel with people who share your financial philosophy.',
      options: [
        { label: 'Split everything evenly, no matter what people ordered.', value: 10 },
        { label: 'Use an app like Splitwise to track exact amounts.', value: 50 },
        { label: 'I usually end up covering the bill for convenience.', value: 90 }
      ]
    },
    {
      id: 'pacing',
      question: 'It is 8:00 AM on day 3 of the trip. Where are you?',
      context: 'Aligning energy levels and sleep schedules is critical for group harmony.',
      options: [
        { label: 'Already out getting coffee and exploring the neighborhood.', value: 90 },
        { label: 'Waking up slowly, checking emails in bed.', value: 50 },
        { label: 'Still asleep. Please do not wake me before 11 AM.', value: 10 }
      ]
    },
    {
      id: 'spontaneity',
      question: 'The group planned a museum tour, but a local invites you to a secret beach party. What is your vote?',
      context: 'Measures your spontaneity versus commitment to the itinerary.',
      options: [
        { label: 'Stick to the museum. We paid for the tickets.', value: 10 },
        { label: 'Split the group! See you guys at dinner.', value: 50 },
        { label: 'Beach party! Cancel the museum immediately.', value: 90 }
      ]
    }
  ];

  answers = signal<number[]>([50, 50, 50, 50]);

  startQuiz() {
    this.currentView.set('quiz');
  }

  next() {
    if (this.step() < this.questions.length - 1) {
      this.step.update(s => s + 1);
    } else {
      this.submit();
    }
  }

  prev() {
    if (this.step() > 0) {
      this.step.update(s => s - 1);
    }
  }

  updateAnswer(val: string) {
    const arr = [...this.answers()];
    arr[this.step()] = parseInt(val, 10);
    this.answers.set(arr);
  }

  private calculateArchetype(scores: number[]): string {
    const sum = scores.reduce((a, b) => a + b, 0);
    const avg = sum / scores.length;
    if (avg > 75) return 'The Spontaneous Leader';
    if (avg > 45) return 'The Balanced Diplomat';
    return 'The Structured Planner';
  }

  submit() {
    this.isSubmitting.set(true);
    const currentUser = this.authService.currentUser();
    const scores = this.answers();
    
    // Compute archetype locally for display
    const computedArchetype = this.calculateArchetype(scores);
    this.archetype.set(computedArchetype);

    if (!currentUser) {
      // Unauthenticated - just show results locally
      setTimeout(() => {
        this.isSubmitting.set(false);
        this.currentView.set('results');
      }, 500);
      return;
    }

    const payload = {
      openness: scores[3], // map spontaneity
      conscientiousness: scores[2], // map pacing
      extraversion: scores[1], // map budget approach 
      agreeableness: scores[0], // map conflict resolution
      neuroticism: 50 // default
    };

    (this.authService as any).submitPsychometricProfile(payload).subscribe({
      next: () => {
        this.isSubmitting.set(false);
        this.currentView.set('results');
        this.toastService.success('Calibration profile saved successfully.');
      },
      error: (err: any) => {
        this.isSubmitting.set(false);
        this.toastService.error(err.error?.detail || 'Failed to submit profile.');
      }
    });
  }

  goToFeed() {
    this.router.navigate(['/feed']);
  }
}
