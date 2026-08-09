import { Component, signal, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { environment } from '../../environments/environment';
import { AuthService } from '../core/auth.service';
import { ToastService } from '../core/toast.service';

export interface PodSkill {
  id: string;
  category: string;
  title: string;
  description: string;
  estimated_value_cents: number;
  user_id: string;
}

@Component({
  selector: 'rally-skill-swap',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './skill-swap.html',
  styleUrls: ['./skill-swap.scss']
})
export class SkillSwap implements OnInit {
  private http = inject(HttpClient);
  public authService = inject(AuthService);
  private router = inject(Router);
  private toastService = inject(ToastService);

  skills = signal<PodSkill[]>([]);
  isLoading = signal(false);

  // Form signals
  showModal = signal(false);
  newCategory = signal('photography');
  newTitle = signal('');
  newDescription = signal('');
  newValueDollars = signal(100);

  // Quote modal signals
  showQuoteModal = signal(false);
  selectedSkill = signal<PodSkill | null>(null);
  quoteOffsetDollars = signal(50);
  quoteNote = signal('');

  ngOnInit() {
    this.loadSkills();
  }

  loadSkills() {
    this.isLoading.set(true);
    this.http.get<PodSkill[]>(`${environment.apiUrl}/trips/skills/all`).subscribe({
      next: (data) => {
        this.skills.set(data || []);
        this.isLoading.set(false);
      },
      error: () => {
        this.toastService.error('Failed to load skills.');
        this.isLoading.set(false);
      }
    });
  }

  openPostModal() {
    if (!this.authService.getToken()) {
      this.toastService.info('Please sign in to post a skill.');
      this.router.navigate(['/login']);
      return;
    }
    this.showModal.set(true);
  }

  closePostModal() {
    this.showModal.set(false);
  }

  addSkill() {
    if (!this.newTitle()) {
      this.toastService.warning('Skill title is required.');
      return;
    }

    const payload = {
      category: this.newCategory(),
      title: this.newTitle(),
      description: this.newDescription(),
      estimated_value_cents: this.newValueDollars() * 100
    };

    this.http.post<PodSkill>(`${environment.apiUrl}/trips/skills/standalone`, payload).subscribe({
      next: () => {
        this.closePostModal();
        this.loadSkills();
        this.toastService.success('Skill listing published successfully.');
      },
      error: (err) => {
        this.toastService.error(err.error?.detail || 'Failed to list skill.');
      }
    });
  }

  openQuoteModal(skill: PodSkill) {
    if (!this.authService.getToken()) {
      this.toastService.info('Please sign in to send a quote.');
      this.router.navigate(['/login']);
      return;
    }
    this.selectedSkill.set(skill);
    this.quoteOffsetDollars.set(Math.round(skill.estimated_value_cents / 200));
    this.showQuoteModal.set(true);
  }

  closeQuoteModal() {
    this.showQuoteModal.set(false);
    this.selectedSkill.set(null);
  }

  sendQuotation() {
    const s = this.selectedSkill();
    if (!s) return;

    this.toastService.success('Quotation sent to the host successfully.');
    this.closeQuoteModal();
  }
}
