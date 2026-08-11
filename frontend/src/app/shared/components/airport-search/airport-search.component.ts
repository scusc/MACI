import { Component, forwardRef, OnInit, HostListener, ElementRef } from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';
import { CommonModule } from '@angular/common';

export interface Airport {
  iata: string;
  name: string;
  city: string;
  country: string;
}

export interface GroupedAirports {
  country: string;
  cities: {
    city: string;
    airports: Airport[];
  }[];
}

let cachedAirportsPromise: Promise<Airport[]> | null = null;

@Component({
  selector: 'app-airport-search',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './airport-search.component.html',
  styleUrls: ['./airport-search.component.scss'],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => AirportSearchComponent),
      multi: true
    }
  ]
})
export class AirportSearchComponent implements OnInit, ControlValueAccessor {
  allAirports: Airport[] = [];
  filteredGroups: GroupedAirports[] = [];
  
  searchTerm = '';
  value = '';
  isOpen = false;
  isLoading = true;

  onChange = (val: string) => {};
  onTouched = () => {};

  constructor(private el: ElementRef) {}

  async ngOnInit() {
    if (!cachedAirportsPromise) {
      cachedAirportsPromise = fetch('/assets/data/airports.json')
        .then(res => res.json())
        .catch(err => {
            console.error("Failed to load airports", err);
            return [];
        });
    }
    this.allAirports = await cachedAirportsPromise;
    this.isLoading = false;
  }

  writeValue(val: string): void {
    this.value = val || '';
    this.searchTerm = this.value;
  }

  registerOnChange(fn: any): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: any): void {
    this.onTouched = fn;
  }
  
  @HostListener('document:click', ['$event'])
  clickout(event: any) {
    if (!this.el.nativeElement.contains(event.target)) {
      this.isOpen = false;
    }
  }

  onInput(event: any) {
    this.searchTerm = event.target.value;
    this.value = this.searchTerm;
    this.onChange(this.value);
    
    if (this.searchTerm.length >= 2) {
      this.filterAirports();
      this.isOpen = true;
    } else {
      this.isOpen = false;
    }
  }

  onFocus() {
    if (this.searchTerm.length >= 2 && this.allAirports.length > 0) {
      this.filterAirports();
      this.isOpen = true;
    }
  }

  selectAirport(airport: Airport) {
    this.value = airport.iata;
    this.searchTerm = airport.iata;
    this.onChange(this.value);
    this.isOpen = false;
  }

  filterAirports() {
    const term = this.searchTerm.toLowerCase();
    
    // Prioritize exact IATA matches
    const exactIata = this.allAirports.filter(a => a.iata.toLowerCase() === term);
    
    // Find other matches
    let others = this.allAirports.filter(a => 
      a.iata.toLowerCase() !== term && (
      a.name.toLowerCase().includes(term) || 
      a.city.toLowerCase().includes(term) || 
      a.country.toLowerCase().includes(term) ||
      a.iata.toLowerCase().includes(term)
    ));
    
    // Combine and limit
    const matches = [...exactIata, ...others].slice(0, 60);
    
    // Group by Country -> City
    const grouped = new Map<string, Map<string, Airport[]>>();
    
    for (const a of matches) {
      if (!grouped.has(a.country)) {
        grouped.set(a.country, new Map());
      }
      const countryGroup = grouped.get(a.country)!;
      if (!countryGroup.has(a.city)) {
        countryGroup.set(a.city, []);
      }
      countryGroup.get(a.city)!.push(a);
    }
    
    // Convert to nested array structure
    this.filteredGroups = Array.from(grouped.entries()).map(([country, cityMap]) => ({
      country,
      cities: Array.from(cityMap.entries()).map(([city, airports]) => ({
        city,
        airports
      }))
    }));
  }
}
