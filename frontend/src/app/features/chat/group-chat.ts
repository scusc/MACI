import { Component, inject, OnInit, OnDestroy, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChatService } from '../../core/chat.service';

@Component({
  selector: 'app-group-chat',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './group-chat.html',
  styleUrl: './group-chat.scss',
})
export class GroupChat implements OnInit, OnDestroy {
  chatService = inject(ChatService);
  
  newMessage = signal('');
  
  // ZK Privacy & Handshake state
  hasVotedReveal = signal(false);
  isIdentityRevealed = signal(false);

  ngOnInit() {
    this.chatService.connect('demo-pool-123');
  }

  ngOnDestroy() {
    this.chatService.disconnect();
  }

  voteToRevealIdentity() {
    this.hasVotedReveal.set(true);
    // Simulate double-opt-in handshake unlock
    setTimeout(() => {
      this.isIdentityRevealed.set(true);
    }, 1200);
  }

  sendMessage() {
    const text = this.newMessage().trim();
    if (text) {
      this.chatService.sendMessage(text);
      this.newMessage.set('');
    }
  }

  handleKeyDown(event: KeyboardEvent) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendMessage();
    }
  }
}
