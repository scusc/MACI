import re

with open('src/app/features/trip-architect/trip-architect.component.ts', 'r') as f:
    content = f.read()

directive_code = """
import flatpickr from 'flatpickr';
import { Directive, ElementRef, OnInit, OnDestroy, Input, inject } from '@angular/core';

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
"""

# Inject the directive definition before @Component
content = content.replace("@Component({", directive_code + "\n@Component({")

# Add the directive to the imports array of the component
content = content.replace("imports: [CommonModule, FormsModule, ReactiveFormsModule]", "imports: [CommonModule, FormsModule, ReactiveFormsModule, FlatpickrRangeDirective]")

# Now handle the custom validation/min date tracking logic if needed, 
# But using a getter in the template for `minDate` is easier. We will do that in HTML.

with open('src/app/features/trip-architect/trip-architect.component.ts', 'w') as f:
    f.write(content)

print("Updated trip-architect.component.ts with Flatpickr Directive")
