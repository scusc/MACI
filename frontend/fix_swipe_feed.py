import re

with open('src/app/features/swipe-feed.html', 'r') as f:
    content = f.read()

# Replace openCreateModal with goToArchitect
content = content.replace('openCreateModal()', 'goToArchitect()')

# Remove the AI Quote UI block which starts at <div class="ai-quote-container"> and ends at its closing div
# I'll just regex replace the block
pattern = re.compile(r'<div class="ai-quote-container">.*?</div>\s*</div>\s*</div>', re.DOTALL)
replacement = '''<div class="input-with-button">
              <input type="number" [ngModel]="postCost()" (ngModelChange)="postCost.set($event)" class="form-input" />
            </div>
          </div>
        </div>'''
content = re.sub(pattern, replacement, content)

with open('src/app/features/swipe-feed.html', 'w') as f:
    f.write(content)
