I will optimize the UI layout of `frontend/src/views/ReviewTimeline.vue` to address the "weird" layout issues, focusing on visual hierarchy, alignment, and spacing.

### Proposed Changes:

1.  **Overview Card (Top Stats)**:
    *   Remove the vertical dividers for a cleaner look.
    *   Use `justify-content: space-around` to distribute items evenly.
    *   Increase the font size of the numerical values for better emphasis.

2.  **Timeline Item (Video Segments)**:
    *   **Index Badge**: Move the badge *inside* the thumbnail (top-left corner) to avoid the "hanging off the edge" look which can appear broken.
    *   **Actions Layout**:
        *   Center the **Drag Handle** vertically on the right side for easier access and better aesthetics.
        *   Move the **Delete Button** to the top-right corner of the content area or align it with the title, preventing the awkward large gap between the drag handle and delete button.
    *   **Spacing**: Increase gap between thumbnail and text content.
    *   **Tags**: Style the "AI Confidence" label as a cleaner tag/badge.

3.  **Script Section**:
    *   Improve the header alignment of "AI Commentary Script" and the "Regenerate" button.
    *   Style the text area container to blend better with the page.

4.  **Bottom Action Bar**:
    *   Ensure padding respects the device safe area (e.g., for iPhone X+).
    *   Add a subtle top border or shadow to separate it clearly from the content.

### File to Modify:
*   `frontend/src/views/ReviewTimeline.vue`
