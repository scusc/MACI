import re

with open('src/app/features/trip-architect/trip-architect.component.ts', 'r') as f:
    content = f.read()

new_ts = """import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, FormArray, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { PoolService, AIQuoteRequest, AIQuoteResponse, AIQuoteOption, TravelerQuote } from '../../core/pool.service';
import { ToastService } from '../../core/toast.service';

@Component({
  selector: 'app-trip-architect',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule],
  templateUrl: './trip-architect.component.html',
  styleUrls: ['./trip-architect.component.scss']
})
export class TripArchitectComponent {
  private fb = inject(FormBuilder);
  private poolService = inject(PoolService);
  private router = inject(Router);
  private toastService = inject(ToastService);

  viewState: 'input' | 'options' | 'manual-edit' = 'input';

  architectForm: FormGroup = this.fb.group({
    travelers: this.fb.array([this.createTraveler()]),
    itinerary: this.fb.array([this.createLeg()]),
    budget_tier: ['balanced']
  });

  quoteOptions: AIQuoteOption[] = [];
  selectedOption: AIQuoteOption | null = null;
  
  // For manual edit mode
  editingQuoteIndex: number | null = null;
  manualFlightSearchActive = false;

  isLoading = false;
  error = '';

  get travelers() {
    return this.architectForm.get('travelers') as FormArray;
  }

  get itinerary() {
    return this.architectForm.get('itinerary') as FormArray;
  }

  createTraveler(): FormGroup {
    return this.fb.group({
      name: ['', Validators.required],
      origin: ['', Validators.required]
    });
  }

  createLeg(): FormGroup {
    return this.fb.group({
      destination: ['', Validators.required],
      arrival_date: ['', Validators.required],
      departure_date: ['', Validators.required]
    });
  }

  addTraveler() {
    this.travelers.push(this.createTraveler());
  }

  removeTraveler(index: number) {
    if (this.travelers.length > 1) {
      this.travelers.removeAt(index);
    }
  }

  addLeg() {
    this.itinerary.push(this.createLeg());
  }

  removeLeg(index: number) {
    if (this.itinerary.length > 1) {
      this.itinerary.removeAt(index);
    }
  }

  generateQuote() {
    if (this.architectForm.invalid) {
      this.error = 'Please fill out all fields.';
      return;
    }
    
    this.isLoading = true;
    this.error = '';
    this.quoteOptions = [];
    
    const request: AIQuoteRequest = this.architectForm.value;
    
    this.poolService.getAIQuote(request).subscribe({
      next: (res) => {
        this.quoteOptions = res.options || [];
        this.viewState = 'options';
        this.isLoading = false;
      },
      error: (err) => {
        this.error = 'Failed to generate quote. Please try again.';
        this.isLoading = false;
        console.error(err);
      }
    });
  }
  
  selectOption(opt: AIQuoteOption) {
    this.selectedOption = JSON.parse(JSON.stringify(opt)); // Deep copy for editing
    this.viewState = 'manual-edit';
  }
  
  goBack() {
    if (this.viewState === 'manual-edit') {
        this.viewState = 'options';
    } else if (this.viewState === 'options') {
        this.viewState = 'input';
    }
  }
  
  recalculateTotal() {
    if (!this.selectedOption) return;
    let total_flights = 0;
    this.selectedOption.traveler_quotes.forEach(tq => {
        total_flights += tq.individual_cost;
        tq.total_cost = tq.individual_cost + this.selectedOption!.shared_cost_per_person;
    });
  }
  
  publishPool() {
    if (!this.selectedOption) return;
    
    const destination = this.itinerary.at(0).value.destination;
    const start_date = this.itinerary.at(0).value.arrival_date;
    const end_date = this.itinerary.at(this.itinerary.length - 1).value.departure_date;
    
    this.isLoading = true;
    this.poolService.createTrip({
      title: `${destination} Trip (${this.selectedOption.title})`,
      destination: destination,
      start_date: start_date + 'T00:00:00Z',
      end_date: end_date + 'T00:00:00Z',
      description: `Auto-generated itinerary based on ${this.selectedOption.title} tier. ${this.selectedOption.reasoning}`,
      estimated_cost_per_person: this.selectedOption.shared_cost_per_person
    }).subscribe({
      next: () => {
        this.toastService.success('Trip Pool created successfully!');
        this.router.navigate(['/pools']);
      },
      error: (err) => {
        this.toastService.error('Failed to create pool.');
        this.isLoading = false;
      }
    });
  }
}
"""

with open('src/app/features/trip-architect/trip-architect.component.ts', 'w') as f:
    f.write(new_ts)

print("Updated trip-architect.component.ts")
