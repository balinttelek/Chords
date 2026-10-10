def touch_drag(page, x0, y0, x1, y1, steps=12, dt=16):
    """A real touch drag through the DevTools protocol (Playwright's mouse doesn't fire touch pointer events)."""
    s = page.context.new_cdp_session(page)
    s.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x0, "y": y0}]})
    for i in range(1, steps + 1):
        page.wait_for_timeout(dt)
        s.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x0 + (x1 - x0) * i / steps, "y": y0 + (y1 - y0) * i / steps}]})
    s.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
