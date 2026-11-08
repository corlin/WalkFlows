# Review-page usability update

The existing site03 page was inspected in the local browser before and after this change. The initial viewport showed two videos and a map, but reaching analysis sections required scrolling a long page. The area form placed coordinates and many actions in a single dense sequence; the camera selectors had no accessible names.

The page now has a sticky, keyboard-focusable section navigation for replay, analysis window, layout, quality, comparison, transitions and funnel. The area form groups labels above their inputs, wraps its actions on smaller widths and distinguishes primary, secondary and delete actions. Controls have visible keyboard focus, camera selectors have accessible labels and reduced-motion preference disables smooth scrolling. Existing analysis logic, layout storage and source warnings are retained.

Browser checks: the page rendered with both video views; the area link navigated to its section with the navigation still visible; the area form rendered with separate labels and grouped controls. Screenshots were captured under the ignored `data/processed/ux-review/` directory. The fixed-sample cross-scene preparation and Python/JavaScript checks passed. This is not a comprehensive accessibility audit or a substitute for assistive-technology and mobile-device testing.
