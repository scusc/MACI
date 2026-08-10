with open('src/app/features/trip-architect/trip-architect.component.ts', 'r') as f:
    content = f.read()

get_min_date_fn = """
  getMinDate(index: number): string {
    if (index === 0) return 'today';
    const prevLeg = this.itinerary.at(index - 1).value;
    return prevLeg.departure_date || 'today';
  }
"""

content = content.replace("  addLeg() {", get_min_date_fn + "\n  addLeg() {")

with open('src/app/features/trip-architect/trip-architect.component.ts', 'w') as f:
    f.write(content)
print("Added getMinDate to ts")
