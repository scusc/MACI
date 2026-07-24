import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-layout',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './layout.html',
  styleUrl: './layout.scss',
})
export class Layout {}
