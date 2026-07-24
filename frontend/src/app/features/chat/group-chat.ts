import { Component, inject, OnInit, OnDestroy, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { ChatService } from '../../core/chat.service';
import { AuthService } from '../../core/auth.service';

@Component({
  selector: 'app-group-chat',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './group-chat.html',
  styleUrl: './group-chat.scss',
})
export class GroupChat implements OnInit, OnDestroy {
  public chatService = inject(ChatService);
  public authService = inject(AuthService);
  private route = inject(ActivatedRoute);

  poolId = signal('');
  newMessage = signal('');
  
  // ZK Privacy & Handshake state
  hasVotedReveal = signal(false);
  isIdentityRevealed = signal(false);

  // AI Mediator state
  showMediatorModal = signal(false);
  disputeText = signal('');
  isMediating = signal(false);
  mediatorResolution = signal('');

  ngOnInit() {
    this.route.params.subscribe(p => {
      const pid = p['poolId'] || 'demo-pool-123';
      this.poolId.set(pid);
      this.chatService.connect(pid);
    });
  }

  ngOnDestroy() {
    this.chatService.disconnect();
  }

  voteToRevealIdentity() {
    this.hasVotedReveal.set(true);
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

  openMediatorModal() {
    this.showMediatorModal.set(true);
    this.disputeText.set('');
    this.mediatorResolution.set('');
  }

  closeMediatorModal() {
    this.showMediatorModal.set(false);
  }

  submitAIMediation() {
    if (!this.disputeText()) return;
    this.isMediating.set(true);

    this.chatService.requestAIMediator(this.disputeText()).subscribe({
      next: (res) => {
        this.isMediating.set(false);
        this.mediatorResolution.set(res.resolution);
        // Inject AI Mediator response into group chat
        this.chatService.messages.update(msgs => [...msgs, {
          sender: '🤖 Rally AI Mediator',
          text: res.resolution,
          timestamp: new Date(),
          is_ai: true
        }]);
      },
      error: () => {
        this.isMediating.set(false);
        this.mediatorResolution.set('AI Mediator is temporarily unavailable.');
      }
    });
  }
}
