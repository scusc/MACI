import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

export interface Meetup {
  id: string;
  title: string;
  distanceMiles: number;
  escrowCents: number;
  startTime: string;
  hostName: string;
}

@Component({
  selector: 'rally-meetups',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './meetups.html',
  styleUrls: ['./meetups.scss']
})
export class Meetups {
  meetups: Meetup[] = [
    {
      id: 'm1',
      title: 'Local Coffee Vibe Check — Blue Tokai',
      distanceMiles: 0.8,
      escrowCents: 500,
      startTime: 'Today @ 4:00 PM',
      hostName: 'Nomad_94A2F1'
    },
    {
      id: 'm2',
      title: 'Weekend Hike & Trip Planning — Cubbon Park',
      distanceMiles: 2.3,
      escrowCents: 1000,
      startTime: 'Saturday @ 9:00 AM',
      hostName: 'Nomad_B812C4'
    }
  ];

  showCheckInModal = false;
  selectedMeetupId = '';
  enteredPin = '';
  checkInStatus = '';

  openCheckIn(id: string) {
    this.selectedMeetupId = id;
    this.showCheckInModal = true;
    this.enteredPin = '';
    this.checkInStatus = '';
  }

  submitPinCheckIn() {
    if (this.enteredPin.length === 4) {
      this.checkInStatus = '✓ PIN Verified! Escrow hold released cleanly.';
      setTimeout(() => {
        this.showCheckInModal = false;
      }, 1500);
    } else {
      this.checkInStatus = '❌ Invalid PIN. Please ask host for 4-digit PIN.';
    }
  }
}
