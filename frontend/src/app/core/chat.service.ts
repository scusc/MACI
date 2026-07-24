import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { webSocket, WebSocketSubject } from 'rxjs/webSocket';
import { Subscription, Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface ChatMessage {
  sender_id?: string;
  sender?: string;
  content_text?: string;
  text?: string;
  timestamp?: Date;
  is_ai?: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class ChatService {
  private http = inject(HttpClient);
  private socket$!: WebSocketSubject<any>;
  private subscription!: Subscription;

  messages = signal<ChatMessage[]>([]);
  isConnected = signal(false);

  connect(poolId: string) {
    if (!this.socket$ || this.socket$.closed) {
      const token = localStorage.getItem('slice_token') || '';
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsHost = environment.wsUrl ? environment.wsUrl.replace(/^http/, 'ws') : `${wsProtocol}//${window.location.host}`;
      
      const wsUrl = `${wsHost}/api/v1/chat/${poolId}/ws?token=${token}`;
      
      try {
        this.socket$ = webSocket(wsUrl);
        this.subscription = this.socket$.subscribe({
          next: (msg: any) => {
            const parsedText = typeof msg === 'string' ? msg : (msg.content_text || msg.text || JSON.stringify(msg));
            const senderName = msg.sender_id ? (msg.sender_id.length > 8 ? msg.sender_id.substring(0, 8) : msg.sender_id) : 'Traveler';
            this.messages.update(msgs => [...msgs, {
              sender: senderName,
              text: parsedText,
              timestamp: new Date()
            }]);
          },
          error: (err) => {
            console.warn('WebSocket connection fallback:', err);
            this.isConnected.set(false);
          },
          complete: () => {
            this.isConnected.set(false);
          }
        });
        this.isConnected.set(true);
      } catch (e) {
        console.warn('WebSocket error:', e);
      }
    }
  }

  sendMessage(text: string) {
    if (this.socket$ && this.isConnected()) {
      this.socket$.next({ content_text: text });
    } else {
      // Local optimistic update
      this.messages.update(msgs => [...msgs, {
        sender: 'You',
        text: text,
        timestamp: new Date()
      }]);
    }
  }

  requestAIMediator(disputeText: string): Observable<{status: string, resolution: string}> {
    return this.http.post<{status: string, resolution: string}>(`${environment.apiUrl}/chat/mediator`, {
      dispute_text: disputeText
    });
  }

  disconnect() {
    if (this.subscription) this.subscription.unsubscribe();
    if (this.socket$) this.socket$.complete();
    this.isConnected.set(false);
    this.messages.set([]);
  }
}
