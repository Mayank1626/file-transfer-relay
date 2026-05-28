# ZapLink Component Style & Development Guidelines

This document establishes design rules and developer guidelines for adding new features, components, or screens to the ZapLink project, maintaining visual harmony and lightweight performance.

---

## 🎨 Unified Design Tokens

All newly created layouts must utilize the CSS custom properties defined in `/static/css/styles.css` to ensure visual consistency:

```css
:root {
    /* Base Backgrounds */
    --bg-dark: #0a0a0c;
    --card-bg: #141416;
    --card-border: #222226;
    --input-bg: #18181c;
    
    /* Neon gradients */
    --primary-green: #00E676;
    --primary-teal: #00BFA5;
    
    /* Semantic Colors */
    --success: #30d158;
    --error: #ff453a;
    --warning: #ff9f0a;
    --info: #0a84ff;
}
```

### Typography Standards
* **Font Family**: Use the Inter Google Font stack exclusively. Fallback to standard system-sans-serif.
* **Weights**:
  * Body copy: `400` / `500`
  * Action pills and highlights: `600` / `700`
  * Headings: `800` (extra-bold) with a tight letter-spacing: `-0.04em`.
* **Contrast**: All headings should be pure white (`#ffffff`). Secondary meta text should use `--text-muted` (`#86868b`) to ensure readability.

### Form Field Spacing Grid
Spacing must conform to a strict 4px grid system:
* Margins & Paddings: `8px` (small), `12px` (medium), `16px` (large), `24px` (extra-large).
* Component Touch Targets: Tap targets for buttons, inputs, and interactive pills must have a minimum size of **48px x 48px** to remain touch-friendly on mobile viewports.

---

## 🛠️ Unified Core Components

### 1. Primary Action Button
Standard action triggers must inherit direct linear neon gradients:

```html
<button class="btn btn-primary" id="btnId">
    <span class="btn-icon">💡</span> Action Text
</button>
```

### 2. Secondary/Utility Button
For non-primary actions, copy buttons, or option toggles:

```html
<button class="btn btn-secondary" id="btnId">
    📋 Copy Details
</button>
```

### 3. Danger/Cancel Button
For cancellation actions or terminal deletions:

```html
<button class="btn btn-danger" id="btnId">
    ✕ Cancel Transfer
</button>
```

---

## 📢 Centralized Toast Notifications API

Do NOT import heavy external frameworks or create custom inline alert elements. Use the centralized global Toast object:

```javascript
// Display a successful transaction alert
window.Toast.show('File synced successfully!', 'success', 3000);

// Display an error validation message
window.Toast.show('Invalid PIN entry. Please try again.', 'error', 4500);

// Display general instruction feedback
window.Toast.show('Initiating deep-link pairing lookup...', 'info', 2000);
```

### Options:
* `message` *(string)*: Text context of alert.
* `type` *(string)*: Style class matching `'success'`, `'error'`, `'warning'`, or `'info'`.
* `duration` *(number)*: Display duration in milliseconds before automatic deletion (set to `0` to keep toast permanently open until manual dismiss).

---

## 🚀 Scalability Guidelines for Adding New Pages

When developing additional pages, features, or sections for ZapLink, adhere to the following principles:

1. **Keep it Vanilla**: Avoid importing third-party libraries (e.g., jQuery, React, or Bootstrap). Use native Web APIs (`fetch`, `document.getElementById`, `CustomEvent`) to keep the initial page load under 100ms.
2. **Modular Assets**: Create dedicated files for complex components under `/static/components/` and load them as deferred scripts in `index.html` to keep code clean and maintainable.
3. **Responsive Testing Check**: Before releasing changes, test them on a simulated viewport down to **320px** wide. Ensure margins shrink, button panels wrap, and typography scales down gracefully.
4. **Decouple Logic**: Keep networking logic (API queries) completely separated from DOM manipulation routines. Use custom events to bridge updates between components.
