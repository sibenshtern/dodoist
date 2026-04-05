import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-coming-soon',
  standalone: true,
  imports: [RouterLink],
  template: `
    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh;gap:1rem;font-family:sans-serif">
      <h1 style="font-size:2rem;font-weight:700">Coming Soon</h1>
      <p style="color:#6b7280">This feature is not yet available.</p>
      <a routerLink="/home" style="color:#246fe0;text-decoration:none">← Back to dashboard</a>
    </div>
  `,
})
export class ComingSoonComponent {}
