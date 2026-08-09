import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ToastService } from './toast.service';

@Component({
  selector: 'app-toast-container',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="toast-container" aria-live="polite">
      <div
        *ngFor="let toast of toastService.toasts()"
        class="toast"
        [class.toast-success]="toast.type === 'success'"
        [class.toast-error]="toast.type === 'error'"
        [class.toast-warning]="toast.type === 'warning'"
        [class.toast-info]="toast.type === 'info'"
        role="alert"
      >
        <span class="toast-icon">
          {{ toast.type === 'success' ? '✓' : toast.type === 'error' ? '✕' : toast.type === 'warning' ? '!' : 'i' }}
        </span>
        <span class="toast-message">{{ toast.message }}</span>
        <button class="toast-dismiss" (click)="toastService.dismiss(toast.id)" aria-label="Dismiss">&times;</button>
      </div>
    </div>
  `,
  styles: [`
    .toast-icon {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 20px;
      height: 20px;
      border-radius: 50%;
      font-size: 11px;
      font-weight: 700;
      flex-shrink: 0;
    }

    .toast-success .toast-icon { background: #ECFDF5; color: #059669; }
    .toast-error .toast-icon { background: #FEF2F2; color: #DC2626; }
    .toast-warning .toast-icon { background: #FFFBEB; color: #D97706; }
    .toast-info .toast-icon { background: #EFF6FF; color: #2563EB; }

    .toast-message {
      flex: 1;
      color: var(--gray-700);
      line-height: 1.4;
    }

    .toast-dismiss {
      background: none;
      border: none;
      color: var(--gray-400);
      font-size: 1.1rem;
      cursor: pointer;
      padding: 0 2px;
      line-height: 1;
    }

    .toast-dismiss:hover {
      color: var(--gray-900);
    }
  `]
})
export class ToastContainer {
  toastService = inject(ToastService);
}
