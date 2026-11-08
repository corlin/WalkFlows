# Drawing regions on the research floor

The site03 layout form has an optional ?draw on floor? action. Arm it and drag within the scene rectangle to fill the four coordinate fields. Dragging in either direction is supported; the end point is clamped to scene bounds. Starting outside the scene and tiny rectangles are rejected. The draft is not persisted until the user supplies a name, checks the type and clicks Save. An existing selected item is updated only on Save. The button or Escape cancels drawing, and interrupted pointer input does not save anything.

Coordinates use the same scene-to-canvas transform as the existing display, including responsive canvas scaling; they are rounded to three decimal places. This is layout configuration in experimental coordinates, not proof that those coordinates correspond accurately to physical store locations. Keyboard users may continue entering numeric fields directly.

Unit tests cover both drag directions, clamping, outside starts and tiny rectangles. A browser check dragged the canvas and confirmed all four fields were populated and the form remained unsaved. No user layout was modified in that check.
