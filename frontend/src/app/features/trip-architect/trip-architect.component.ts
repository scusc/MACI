import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, FormArray, Validators } from '@angular/forms';
import { PoolService, AIQuoteRequest, AIQuoteResponse } from '../../core/pool.service';

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

  architectForm: FormGroup = this.fb.group({
    travelers: this.fb.array([this.createTraveler()]),
    itinerary: this.fb.array([this.createLeg()]),
    budget_tier: ['balanced']
  });

  quoteResult: AIQuoteResponse | null = null;
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
    
    const request: AIQuoteRequest = this.architectForm.value;
    
    this.poolService.getAIQuote(request).subscribe({
      next: (res) => {
        this.quoteResult = res;
        this.isLoading = false;
      },
      error: (err) => {
        this.error = 'Failed to generate quote. Please try again.';
        this.isLoading = false;
        console.error(err);
      }
    });
  }
}
