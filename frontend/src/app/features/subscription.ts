import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'rally-subscription',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './subscription.html',
  styleUrls: ['./subscription.scss']
})
export class Subscription {
  isSubscribed = false;
  isUpgrading = false;

  upgradeToTrustPassport() {
    this.isUpgrading = true;
    setTimeout(() => {
      this.isSubscribed = true;
      this.isUpgrading = false;
    }, 1500);
  }
}
