with open('src/app/features/trip-architect/trip-architect.component.html', 'r') as f:
    content = f.read()

# Replace the lower half (where quoteResult was) with the new states
# First, find where `quoteResult` rendering started.
import re

html_input_form = content.split('<!-- Loading State -->')[0]

new_html = html_input_form + """
    <!-- Loading State -->
    <div class="loading-state" *ngIf="isLoading">
      <div class="spinner"></div>
      <p>AI is orchestrating your trip...</p>
    </div>

    <!-- Error State -->
    <div class="error-banner" *ngIf="error">
      {{ error }}
    </div>

    <!-- OPTIONS VIEW -->
    <div class="options-view" *ngIf="viewState === 'options' && !isLoading">
      <div class="section-header">
        <h2><i class="icon-sparkles"></i> AI Generated Options</h2>
        <button type="button" class="btn-secondary" (click)="goBack()">Back to Details</button>
      </div>
      
      <div class="options-grid">
        <div class="option-card" *ngFor="let opt of quoteOptions">
          <div class="opt-header">
            <h3>{{opt.title}}</h3>
            <div class="opt-price-tag">${{opt.shared_cost_per_person}} <span>/ person base</span></div>
          </div>
          
          <div class="opt-hotel" *ngIf="opt.hotel_details">
            <img *ngIf="opt.hotel_details.image_url" [src]="opt.hotel_details.image_url" alt="Hotel">
            <div class="hotel-info">
              <strong>{{opt.hotel_details.name}}</strong>
              <span class="rating">★ {{opt.hotel_details.rating}}</span>
            </div>
            <div class="hotel-amenities">
              <span class="badge" *ngFor="let am of opt.hotel_details.amenities">{{am}}</span>
            </div>
          </div>
          
          <p class="opt-reasoning">{{opt.reasoning}}</p>
          
          <button class="btn-primary select-btn" (click)="selectOption(opt)">Customize & Select</button>
        </div>
      </div>
    </div>

    <!-- MANUAL EDIT VIEW -->
    <div class="manual-edit-view" *ngIf="viewState === 'manual-edit' && selectedOption && !isLoading">
      <div class="section-header">
        <h2><i class="icon-edit"></i> Fine-Tune "{{selectedOption.title}}"</h2>
        <div>
          <button type="button" class="btn-secondary" (click)="goBack()" style="margin-right: 8px;">Back to Options</button>
          <button type="button" class="btn-primary" (click)="publishPool()">Publish Pool</button>
        </div>
      </div>
      
      <div class="edit-layout">
        <!-- Accommodation Override -->
        <div class="section-card config-card">
           <h3>Group Accommodation</h3>
           <div class="form-group">
             <label class="form-label">Total Hotel Cost (Shared by Group)</label>
             <div class="input-with-icon">
               <span class="currency-icon">$</span>
               <input type="number" class="form-input" [(ngModel)]="selectedOption.shared_accommodation_total" (change)="selectedOption.shared_cost_per_person = selectedOption.shared_accommodation_total / travelers.length; recalculateTotal()">
             </div>
           </div>
           <p class="cost-per-person">Each person pays: <strong>${{selectedOption.shared_cost_per_person}}</strong></p>
           <a *ngIf="selectedOption.hotel_evidence" [href]="selectedOption.hotel_evidence" target="_blank" class="btn-link">View Live Hotels</a>
        </div>
        
        <!-- Individual Flights Override -->
        <div class="matrix-card">
          <h3>Individual Flight Costs</h3>
          <table class="premium-table">
            <thead>
              <tr>
                <th>Traveler</th>
                <th>Flight Itinerary</th>
                <th>Flight Cost (Manual Override)</th>
                <th>Total Cost</th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let tq of selectedOption.traveler_quotes; let i = index">
                <td>
                  <div class="traveler-name">{{tq.name}}</div>
                  <div class="traveler-origin">{{tq.origin}}</div>
                </td>
                <td class="route-cell">
                  <div class="verbose-flight" *ngFor="let f of tq.flights">
                    <strong>{{f.airline}} {{f.flight_number}}</strong>
                    <span>{{f.departure_time}} - {{f.arrival_time}} ({{f.duration}})</span>
                  </div>
                  <a *ngIf="tq.flight_evidence" [href]="tq.flight_evidence" target="_blank" class="btn-link sm">Search Alternatives</a>
                </td>
                <td class="cost individual-cost">
                  <div class="input-with-icon small">
                    <span class="currency-icon">$</span>
                    <input type="number" class="form-input" [(ngModel)]="tq.individual_cost" (change)="recalculateTotal()">
                  </div>
                </td>
                <td class="cost total-cost">${{tq.total_cost}}</td>
              </tr>
            </tbody>
          </table>
        </div>
        
      </div>
    </div>

  </div>
</div>
"""

# Apply the structural changes to only show the input form if viewState === 'input'
new_html = new_html.replace('<!-- Input Form -->', '<div class="input-form" *ngIf="viewState === \'input\' && !isLoading">')
new_html = new_html.replace('<!-- Loading State -->', '</div>\n\n    <!-- Loading State -->')


with open('src/app/features/trip-architect/trip-architect.component.html', 'w') as f:
    f.write(new_html)

print("Updated trip-architect.component.html")
