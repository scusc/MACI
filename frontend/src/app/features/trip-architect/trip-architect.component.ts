import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, FormArray, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { PoolService, AIQuoteRequest, AIQuoteResponse, AIQuoteOption, TravelerQuote } from '../../core/pool.service';
import { TravelService } from '../../core/travel.service';
import { ToastService } from '../../core/toast.service';
import { AirportSearchComponent } from '../../shared/components/airport-search/airport-search.component';


import flatpickr from 'flatpickr';
import { Directive, ElementRef, OnInit, OnDestroy, Input, ChangeDetectorRef } from '@angular/core';

@Directive({
  selector: '[appFlatpickrRange]',
  standalone: true
})
export class FlatpickrRangeDirective implements OnInit, OnDestroy {
  private el = inject(ElementRef);
  private fpInstance: any;
  
  @Input('appFlatpickrRange') formGroup!: FormGroup;
  @Input() minDate: string | Date = 'today';

  ngOnInit() {
    this.fpInstance = flatpickr(this.el.nativeElement, {
      mode: 'range',
      minDate: this.minDate,
      dateFormat: 'Y-m-d',
      onChange: (selectedDates: Date[], dateStr: string) => {
        if (selectedDates.length === 2 && this.formGroup) {
          // Format correctly for YYYY-MM-DD to avoid timezone shifts
          const d1 = selectedDates[0];
          const d2 = selectedDates[1];
          const formatStr = (d: Date) => {
              const m = (d.getMonth() + 1).toString().padStart(2, '0');
              const day = d.getDate().toString().padStart(2, '0');
              return `${d.getFullYear()}-${m}-${day}`;
          };
          this.formGroup.patchValue({
            arrival_date: formatStr(d1),
            departure_date: formatStr(d2)
          });
        } else if (this.formGroup) {
           this.formGroup.patchValue({
            arrival_date: '',
            departure_date: ''
          });
        }
      }
    });
  }

  ngOnDestroy() {
    if (this.fpInstance) {
      this.fpInstance.destroy();
    }
  }
}

@Component({
  selector: 'app-trip-architect',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule, FlatpickrRangeDirective, AirportSearchComponent],
  templateUrl: './trip-architect.component.html',
  styleUrls: ['./trip-architect.component.scss']
})
export class TripArchitectComponent {
  private fb = inject(FormBuilder);
  private poolService = inject(PoolService);
  private router = inject(Router);
  private toastService = inject(ToastService);
  private cdr = inject(ChangeDetectorRef);
  private travelService = inject(TravelService);

  viewState: 'input' | 'options' | 'manual-edit' = 'input';

  architectForm: FormGroup = this.fb.group({
    travelers: this.fb.array([this.createTraveler()]),
    itinerary: this.fb.array([this.createLeg()]),
    budget_tier: ['balanced']
  });

  isTierDropdownOpen = false;

  toggleTierDropdown() {
    this.isTierDropdownOpen = !this.isTierDropdownOpen;
  }

  selectTier(tier: string) {
    this.architectForm.patchValue({ budget_tier: tier });
    this.isTierDropdownOpen = false;
  }

  get selectedTierLabel() {
    const tier = this.architectForm.get('budget_tier')?.value;
    switch (tier) {
      case 'budget': return 'Budget';
      case 'balanced': return 'Standard';
      case 'luxury': return 'Premium';
      default: return 'Standard';
    }
  }

  quoteOptions: AIQuoteOption[] = [];
  selectedOption: AIQuoteOption | null = null;
  
  // For manual edit mode
  editingQuoteIndex: number | null = null;
  manualFlightSearchActive = false;

  isLoading = false;
  error = '';

  // Publish Modal State
  showPublishModal = false;
  draftTitle = '';
  draftDescription = '';
  isRefining = false;

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


  getMinDate(index: number): string {
    if (index === 0) return 'today';
    const prevLeg = this.itinerary.at(index - 1).value;
    return prevLeg.departure_date || 'today';
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
        try {
          if (!res) throw new Error("Empty response");
          this.quoteOptions = res.options || [];
          // Fallback if backend returns an array directly
          if (Array.isArray(res)) {
              this.quoteOptions = res;
          }
          this.viewState = 'options';
        } catch (e) {
          console.error(e);
          this.error = 'Invalid response format.';
        } finally {
          this.isLoading = false;
          this.cdr.detectChanges();
        }
      },
      error: (err) => {
        this.error = 'Failed to generate quote. Please try again.';
        this.isLoading = false;
        this.cdr.detectChanges();
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

  getTotalPoolGoal(): number {
    if (!this.selectedOption) return 0;
    let total = this.selectedOption.shared_accommodation_total;
    for (const tq of this.selectedOption.traveler_quotes) {
      total += tq.individual_cost;
    }
    return total;
  }
  
  publishPool() {
    if (!this.selectedOption) return;
    
    const destination = this.itinerary.at(0).value.destination;
    
    // Pre-fill defaults and open modal
    this.draftTitle = `${destination} Trip (${this.selectedOption.title})`;
    this.draftDescription = `Auto-generated itinerary based on ${this.selectedOption.title} tier. ${this.selectedOption.reasoning}`;
    this.showPublishModal = true;
  }

  cancelPublish() {
    this.showPublishModal = false;
  }

  refineWithAI() {
    if (!this.draftTitle || !this.draftDescription) return;
    this.isRefining = true;
    this.travelService.refineTripDetails(this.draftTitle, this.draftDescription).subscribe({
      next: (res) => {
        this.draftTitle = res.title;
        this.draftDescription = res.description;
        this.isRefining = false;
        this.cdr.detectChanges();
        this.toastService.success('Trip details magically refined!');
      },
      error: (err) => {
        this.isRefining = false;
        this.cdr.detectChanges();
        this.toastService.error('Failed to refine with AI.');
      }
    });
  }

  confirmPublish() {
    if (!this.selectedOption) return;
    
    const destination = this.itinerary.at(0).value.destination;
    const start_date = this.itinerary.at(0).value.arrival_date;
    const end_date = this.itinerary.at(this.itinerary.length - 1).value.departure_date;
    
    this.isLoading = true;
    this.poolService.createTrip({
      title: this.draftTitle,
      destination: destination,
      start_date: start_date + 'T00:00:00Z',
      end_date: end_date + 'T00:00:00Z',
      description: this.draftDescription,
      estimated_cost_per_person: this.selectedOption.shared_cost_per_person
    }).subscribe({
      next: () => {
        this.isLoading = false;
        this.showPublishModal = false;
        this.cdr.detectChanges();
        this.toastService.success('Trip Pool created successfully!');
        this.router.navigate(['/pools']);
      },
      error: (err) => {
        this.toastService.error('Failed to create pool.');
        this.isLoading = false;
        this.cdr.detectChanges();
      }
    });
  }
}
