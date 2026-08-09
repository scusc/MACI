import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChatService, ChatMessage } from '../../core/chat.service';
import { ToastService } from '../../core/toast.service';

@Component({
  selector: 'app-ai-chat',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './ai-chat.html',
  styleUrl: './ai-chat.scss',
})
export class AiChat {
  private chatService = inject(ChatService);
  private toastService = inject(ToastService);

  messages = signal<ChatMessage[]>([
    {
      sender: 'AI Concierge',
      text: 'Hello! I am your Rally AI Concierge. I can help you find travel pools, suggest itineraries, or mediate disputes. What can I help you with today?',
      timestamp: new Date(),
      is_ai: true
    }
  ]);
  
  newMessage = signal('');
  isTyping = signal(false);

  sendMessage() {
    const text = this.newMessage().trim();
    if (!text) return;

    // Add user message
    this.messages.update(msgs => [...msgs, {
      sender: 'You',
      text: text,
      timestamp: new Date(),
      is_ai: false
    }]);

    this.newMessage.set('');
    this.isTyping.set(true);

    this.chatService.sendDirectMessageToAI(text).subscribe({
      next: (res) => {
        this.isTyping.set(false);
        this.messages.update(msgs => [...msgs, {
          sender: 'AI Concierge',
          text: res.response || (res as any).resolution,
          timestamp: new Date(),
          is_ai: true
        }]);
      },
      error: () => {
        this.isTyping.set(false);
        this.toastService.error('AI Concierge is currently unavailable.');
      }
    });
  }

  handleKeyDown(event: KeyboardEvent) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendMessage();
    }
  }
}
