import { Component, signal, computed, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AssetService } from '../core/asset.service';

interface Asset {
  id: string;
  title: string;
  description: string;
  category: string;
  location: string;
  total_price: number;
  media_url: string;
}

const FALLBACK_ASSETS: Asset[] = [
  {
    id: 'a1',
    title: 'Luxury Cliffside Villa & Co-Living Pod',
    description: 'Shielded Pod: Introvert-friendly pacing, shared infinity pool & high-speed Starlink for digital nomads.',
    category: 'luxury',
    location: 'Uluwatu, Bali, Indonesia',
    total_price: 3500,
    media_url: 'https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=1000'
  },
  {
    id: 'a2',
    title: 'Eco-Lodge Jungle Retreat',
    description: 'Shielded Pod: Yoga mornings, organic chef, & local language interpreter included in pod skill swap.',
    category: 'wellness',
    location: 'Ubud, Bali, Indonesia',
    total_price: 2200,
    media_url: 'https://images.unsplash.com/photo-1540555700478-4be289fbecef?w=1000'
  }
];

@Component({
  selector: 'app-swipe-feed',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './swipe-feed.html',
  styleUrl: './swipe-feed.scss',
})
export class SwipeFeed implements OnInit {
  private assetService = inject(AssetService);
  
  assets = signal<Asset[]>(FALLBACK_ASSETS);
  currentIndex = signal(0);
  isLoading = signal(false);

  ngOnInit() {
    const checkIn = new Date();
    checkIn.setDate(checkIn.getDate() + 30);
    const checkOut = new Date();
    checkOut.setDate(checkOut.getDate() + 35);
    
    this.assetService.searchInventory(
      'Villas in Bali', 
      checkIn.toISOString().split('T')[0], 
      checkOut.toISOString().split('T')[0], 
      'luxury'
    ).subscribe({
      next: (data) => {
        if (data && data.length > 0) {
          const mappedAssets = data.map(a => ({
            ...a,
            media_url: a.media_urls && a.media_urls.length > 0 ? a.media_urls[0] : FALLBACK_ASSETS[0].media_url
          }));
          this.assets.set(mappedAssets);
        }
      },
      error: () => {
        // Fallback data remains active
      }
    });
  }

  currentAsset = computed(() => {
    const assetsList = this.assets();
    const index = this.currentIndex();
    return index < assetsList.length ? assetsList[index] : null;
  });

  isEmpty = computed(() => this.currentAsset() === null);

  swipe(direction: 'left' | 'right') {
    if (this.isEmpty()) return;
    this.currentIndex.update(i => i + 1);
  }
}
