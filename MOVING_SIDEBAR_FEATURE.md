# Moving Sidebar Feature

## Overview
The website now includes a **moving sidebar feature** that allows you to toggle the sidebar between the left and right positions on the page.

## How It Works

### Toggle Button
- A **position toggle button** is located in the top-right corner of the sidebar
- The button displays:
  - **Chevron Right (→)** when the sidebar is on the left (click to move it right)
  - **Chevron Left (←)** when the sidebar is on the right (click to move it left)

### Features
1. **Smooth Animation**: The sidebar moves smoothly between left and right positions with a 0.4-second transition
2. **Persistent State**: Your sidebar position preference is saved in localStorage and restored when you revisit the page
3. **Responsive Design**: Works seamlessly on both desktop and mobile devices
4. **Visual Feedback**: 
   - The button has hover effects (background color change, scale, border highlight)
   - Smooth transitions for margin adjustments on the main content area

## Technical Implementation

### Modified Components
1. **Sidebar.vue**
   - Added `sidebarPosition` reactive state ('left' or 'right')
   - Added `toggleSidebarPosition()` method
   - Added position toggle button with dynamic icons
   - Added CSS class `sidebar-right` for styling when on the right
   - Saves position to localStorage for persistence

2. **Dashboard.vue**
   - Added `sidebarPosition` reactive state to track sidebar position
   - Listens for localStorage changes via the 'storage' event
   - Applies `sidebar-right` class to main-content when sidebar is on the right
   - Adjusts margins dynamically: `margin-left` for left position, `margin-right` for right position

### CSS Transitions
- Desktop sidebar: `transition: width 0.3s, left 0.4s ease, right 0.4s ease`
- Main content: `transition: margin-left 0.3s, margin-right 0.3s`
- Toggle button: `transition: all 0.3s ease`

## Usage
1. Click the **chevron button** (→/←) in the top-right corner of the sidebar
2. The sidebar smoothly animates to the opposite side
3. Your preference is automatically saved and will be remembered on future visits

## Styling Details
- **Toggle Button Position**: Fixed at top-right of sidebar (`top: 16px, right: 16px`)
- **Toggle Button Colors**:
  - Background: `rgba(99, 102, 241, 0.1)`
  - Border: `rgba(99, 102, 241, 0.3)`
  - Text: `#818CF8`
  - Hover: Brighter colors with scale effect
- **Sidebar Border**: Switches from right (left position) to left (right position)
- **Shadow**: Adjusts direction based on position (inset left vs inset right)

## Browser Compatibility
This feature uses:
- `localStorage` for persistence (all modern browsers)
- CSS transitions (all modern browsers)
- Vue 3 reactive features and lifecycle hooks
