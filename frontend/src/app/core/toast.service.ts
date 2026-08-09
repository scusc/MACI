import { Injectable, signal } from '@angular/core';

export interface Toast {
  id: number;
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
  duration: number;
}

@Injectable({ providedIn: 'root' })
export class ToastService {
  toasts = signal<Toast[]>([]);
  private nextId = 0;

  show(message: string, type: Toast['type'] = 'info', duration = 4000) {
    const id = this.nextId++;
    const toast: Toast = { id, type, message, duration };
    this.toasts.update(t => [...t, toast]);

    if (duration > 0) {
      setTimeout(() => this.dismiss(id), duration);
    }
  }

  success(message: string, duration = 4000) {
    this.show(message, 'success', duration);
  }

  error(message: string, duration = 6000) {
    this.show(message, 'error', duration);
  }

  warning(message: string, duration = 5000) {
    this.show(message, 'warning', duration);
  }

  info(message: string, duration = 4000) {
    this.show(message, 'info', duration);
  }

  dismiss(id: number) {
    this.toasts.update(t => t.filter(toast => toast.id !== id));
  }
}
