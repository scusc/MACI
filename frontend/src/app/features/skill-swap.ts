import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

export interface PodSkill {
  id: string;
  category: string;
  title: string;
  description: string;
  estimatedValueCents: number;
  offeredBy: string;
}

@Component({
  selector: 'rally-skill-swap',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './skill-swap.html',
  styleUrls: ['./skill-swap.scss']
})
export class SkillSwap {
  skills: PodSkill[] = [
    {
      id: 's1',
      category: 'photography',
      title: 'Professional 4K Drone Footage',
      description: 'Will shoot 4K aerial video of villa & excursions for the group.',
      estimatedValueCents: 15000,
      offeredBy: 'Alex (Drone Pilot)'
    },
    {
      id: 's2',
      category: 'language',
      title: 'Fluent Local Language Interpreter',
      description: 'Handles all local restaurant orders, market negotiations, and taxi routing.',
      estimatedValueCents: 10000,
      offeredBy: 'Sophia (Polyglot)'
    },
    {
      id: 's3',
      category: 'cooking',
      title: 'Private Chef Breakfast Prep',
      description: 'Will cook fresh healthy group breakfasts for 5 days.',
      estimatedValueCents: 12000,
      offeredBy: 'Marco (Culinary Explorer)'
    }
  ];

  newCategory = 'photography';
  newTitle = '';
  newDescription = '';
  newValueDollars = 100;

  addSkill() {
    if (!this.newTitle) return;

    this.skills.push({
      id: 's_' + Date.now(),
      category: this.newCategory,
      title: this.newTitle,
      description: this.newDescription,
      estimatedValueCents: this.newValueDollars * 100,
      offeredBy: 'You (Host)'
    });

    this.newTitle = '';
    this.newDescription = '';
    this.newValueDollars = 100;
  }
}
