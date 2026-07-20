import { Injectable, signal } from '@angular/core';
import { webSocket, WebSocketSubject } from 'rxjs/webSocket';
import { Subscription } from 'rxjs';

export interface ChatMessage {
  sender: string;
  text: string;
  timestamp?: Date;
}

@Injectable({
  providedIn: 'root'
})
export class ChatService {
  private socket$!: WebSocketSubject<any>;
  private subscription!: Subscription;

  // Real-time reactive signal for the chat UI
  messages = signal<ChatMessage[]>([]);
  isConnected = signal(false);

  connect(poolId: string) {
    if (!this.socket$ || this.socket$.closed) {
      // Get the JWT token
      const token = localStorage.getItem('slice_token');
      // Connect to the Asset Service WebSocket endpoint with authentication
      this.socket$ = webSocket(`ws://localhost:8002/ws/chat/${poolId}?token=${token}`);
      
      this.subscription = this.socket$.subscribe({
        next: (msg) => {
          this.messages.update(messages => [...messages, { ...msg, timestamp: new Date() }]);
        },
        error: (err) => {
          console.error('WebSocket Error:', err);
          this.isConnected.set(false);
        },
        complete: () => {
          this.isConnected.set(false);
        }
      });
      
      this.isConnected.set(true);
    }
  }

  sendMessage(text: string) {
    if (this.socket$ && this.isConnected()) {
      this.socket$.next(text);
    }
  }

  disconnect() {
    if (this.subscription) {
      this.subscription.unsubscribe();
    }
    if (this.socket$) {
      this.socket$.complete();
    }
    this.isConnected.set(false);
    this.messages.set([]);
  }
}
