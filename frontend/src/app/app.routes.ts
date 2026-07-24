import { Routes } from '@angular/router';

export const appRoutes: Routes = [
  { path: 'login', loadComponent: () => import('./features/auth/login').then(m => m.Login) },
  { path: 'register', loadComponent: () => import('./features/auth/register').then(m => m.Register) },
  { path: 'quiz', loadComponent: () => import('./features/psychometric-quiz').then(m => m.PsychometricQuiz) },
  { path: 'feed', loadComponent: () => import('./features/swipe-feed').then(m => m.SwipeFeed) },
  { path: 'pools', loadComponent: () => import('./features/pool-dashboard').then(m => m.PoolDashboard) },
  { path: 'skills', loadComponent: () => import('./features/skill-swap').then(m => m.SkillSwap) },
  { path: 'meetups', loadComponent: () => import('./features/meetups').then(m => m.Meetups) },
  { path: 'subscription', loadComponent: () => import('./features/subscription').then(m => m.Subscription) },
  { path: 'chat/:poolId', loadComponent: () => import('./features/chat/group-chat').then(m => m.GroupChat) },
  { path: 'host', loadComponent: () => import('./features/host-dashboard').then(m => m.HostDashboard) },
  { path: '', redirectTo: 'feed', pathMatch: 'full' }
];
