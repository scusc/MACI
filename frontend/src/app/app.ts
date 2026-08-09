import { Component, inject, OnInit } from '@angular/core';
import { RouterModule } from '@angular/router';
import { Layout } from './core/layout';
import { SessionService } from './core/session.service';

@Component({
  imports: [RouterModule, Layout],
  selector: 'app-root',
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App implements OnInit {
  protected title = 'frontend';
  private sessionService = inject(SessionService);

  ngOnInit() {
    this.sessionService.init();
  }
}
