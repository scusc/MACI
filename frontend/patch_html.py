with open('src/app/features/trip-architect/trip-architect.component.html', 'r') as f:
    content = f.read()

# Replace Header
content = content.replace(
    '<h1>Multi-Origin Trip Architect</h1>\n      <p>Coordinate flights from different cities, split shared villas, and let AI build the fairest quote.</p>',
    '<h1>Multi-Origin Trip Architect</h1>\n      <p>Build the perfect group trip seamlessly.</p>'
)

# Replace Sections
content = content.replace('<h2><i class="icon-users"></i> The Group</h2>', '<h2><i class="icon-users"></i> Travelers & Origins</h2>')
content = content.replace('<h2><i class="icon-route"></i> The Itinerary</h2>', '<h2><i class="icon-route"></i> The Convergence Chain</h2>')

# Remove the hint text that explicitly explains it if user wanted it to be self-explanatory
content = content.replace(
    '<p class="form-hint" style="margin-bottom: var(--space-4); color: var(--gray-500); font-size: var(--text-sm);">\n          Flights are automatically calculated based on your origin and these dates. You fly out on the first Check-in date, and return on the final Check-out date.\n        </p>',
    ''
)

# Replace the two date inputs with one Flatpickr range input
old_dates = """            <div class="form-row">
              <div class="form-group">
                <label class="form-label">Start Date (Check-in)</label>
                <input class="form-input custom-date" type="date" formControlName="arrival_date">
              </div>
              <div class="form-group">
                <label class="form-label">End Date (Check-out)</label>
                <input class="form-input custom-date" type="date" formControlName="departure_date">
              </div>
            </div>"""

new_date = """            <div class="form-group">
              <label class="form-label">Travel Dates (Check-in to Check-out)</label>
              <input class="form-input custom-date" type="text" placeholder="Select date range" [appFlatpickrRange]="leg" [minDate]="getMinDate(i)">
              <!-- We still need the controls in the form group, but FlatpickrDirective patches them -->
              <input type="hidden" formControlName="arrival_date">
              <input type="hidden" formControlName="departure_date">
            </div>"""

content = content.replace(old_dates, new_date)

# Replace AI Buzzwords in Options/Results
content = content.replace('<h2><i class="icon-sparkles"></i> AI Generated Options</h2>', '<h2><i class="icon-sparkles"></i> Review Options</h2>')
content = content.replace('<span *ngIf="!isLoading">Build Smart Quote</span>', '<span *ngIf="!isLoading">Generate Estimate</span>')
content = content.replace('<p>AI is orchestrating your trip...</p>', '<p>Generating blueprint...</p>')

with open('src/app/features/trip-architect/trip-architect.component.html', 'w') as f:
    f.write(content)

print("HTML Patched!")
