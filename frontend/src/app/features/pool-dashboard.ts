import { Component, signal, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { PoolService, Pool } from '../core/pool.service';
import { AuthService } from '../core/auth.service';



@Component({
  selector: 'app-pool-dashboard',
  imports: [CommonModule],
  templateUrl: './pool-dashboard.html',
  styleUrl: './pool-dashboard.scss',
})
export class PoolDashboard {
  private poolService = inject(PoolService);
  private authService = inject(AuthService);
  
  pools = signal<Pool[]>([]);
  isLoading = signal(true);
  currentUser = this.authService.currentUser;

  ngOnInit() {
    this.poolService.getMyPools().subscribe({
      next: (data) => {
        // Mock augmentation for UI display since the backend model doesn't return joined asset titles directly yet
        // In a real API, the backend should return a joined model
        const augmentedData = data.map(p => ({
          ...p,
          assetTitle: p.assetTitle || `Asset ID: ${p.asset_id.substring(0, 8)}`,
          slicesCommitted: p.slicesCommitted || 1,
          totalSlices: p.totalSlices || 4,
          costPerSlice: p.costPerSlice || 500
        }));
        this.pools.set(augmentedData);
        this.isLoading.set(false);
      },
      error: (err) => {
        console.error('Failed to load pools', err);
        this.isLoading.set(false);
      }
    });
  }

  cancelAuthorization(poolId: string) {
    if (confirm('Are you sure you want to cancel your escrow authorization? Your slot will be released.')) {
      this.poolService.cancelCommitment(poolId).subscribe({
        next: () => {
          // Re-fetch pools
          this.ngOnInit();
        },
        error: (err) => alert('Failed to cancel authorization.')
      });
    }
  }

  getStatusClass(status: string): string {
    return `status-badge status-${status}`;
  }

  startKYC() {
    const user = this.currentUser();
    if (user) {
      this.authService.startKYC(user.id).subscribe({
        next: (res) => window.location.href = res.verification_url,
        error: (err) => alert('Failed to initialize Stripe Identity.')
      });
    }
  }
}
