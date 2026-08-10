import re

with open('src/app/features/trip-architect/trip-architect.component.ts', 'r') as f:
    content = f.read()

# Fix duplicate inject
content = content.replace("import { Directive, ElementRef, OnInit, OnDestroy, Input, inject }", "import { Directive, ElementRef, OnInit, OnDestroy, Input }")

with open('src/app/features/trip-architect/trip-architect.component.ts', 'w') as f:
    f.write(content)

with open('src/app/features/trip-architect/trip-architect.component.html', 'r') as f:
    html = f.read()

# Fix template type error by casting leg to any
html = html.replace('[appFlatpickrRange]="leg"', '[appFlatpickrRange]="$any(leg)"')

with open('src/app/features/trip-architect/trip-architect.component.html', 'w') as f:
    f.write(html)
print("Fixed!")
