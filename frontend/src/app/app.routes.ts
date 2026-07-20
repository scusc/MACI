import { Routes } from '@angular/router';

export const appRoutes: Routes = [
  { path: 'login', loadComponent: () => import('./features/auth/login').then(m => m.Login) },
  { path: 'register', loadComponent: () => import('./features/auth/register').then(m => m.Register) },
  { path: 'feed', loadComponent: () => import('./features/swipe-feed').then(m => m.SwipeFeed) },
  { path: 'pools', loadComponent: () => import('./features/pool-dashboard').then(m => m.PoolDashboard) },
  { path: 'chat/:poolId', loadComponent: () => import('./features/chat/group-chat').then(m => m.GroupChat) },
  { path: 'host', loadComponent: () => import('./features/host-dashboard').then(m => m.HostDashboard) },
  { path: '', redirectTo: 'feed', pathMatch: 'full' }
];
