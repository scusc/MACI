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

@Component({
  selector: 'app-swipe-feed',
  imports: [CommonModule],
  templateUrl: './swipe-feed.html',
  styleUrl: './swipe-feed.scss',
})
export class SwipeFeed {
  private assetService = inject(AssetService);
  
  // Real data store
  assets = signal<Asset[]>([]);
  currentIndex = signal(0);
  isLoading = signal(true);

  ngOnInit() {
    // Fetch live inventory for next month (simulated dates)
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
        // Map the backend model to the frontend model
        const mappedAssets = data.map(a => ({
          ...a,
          media_url: a.media_urls && a.media_urls.length > 0 ? a.media_urls[0] : 'https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?q=80&w=2070'
        }));
        this.assets.set(mappedAssets);
        this.isLoading.set(false);
      },
      error: (err) => {
        console.error('Failed to load assets', err);
        this.isLoading.set(false);
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
    
    // Animate and then move to next
    if (direction === 'right') {
      console.log('Swiped Right on:', this.currentAsset()?.title);
      // Trigger pool creation or join intent
    } else {
      console.log('Swiped Left on:', this.currentAsset()?.title);
    }

    this.currentIndex.update(i => i + 1);
  }
}
