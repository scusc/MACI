import { Component, inject, OnInit, OnDestroy, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChatService } from '../../core/chat.service';

@Component({
  selector: 'app-group-chat',
  imports: [CommonModule, FormsModule],
  templateUrl: './group-chat.html',
  styleUrl: './group-chat.scss',
})
export class GroupChat implements OnInit, OnDestroy {
  chatService = inject(ChatService);
  
  // The input model bound to the chat input field
  newMessage = signal('');

  ngOnInit() {
    // In a real flow, this poolId comes from the Route params
    // Hardcoding a demo poolId for now
    this.chatService.connect('demo-pool-123');
  }

  ngOnDestroy() {
    this.chatService.disconnect();
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
