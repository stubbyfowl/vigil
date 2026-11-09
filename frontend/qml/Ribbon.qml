import QtQuick

// The signature. A ribbon of the last 30 days: it swells and warms as this person drifts from their own normal.
Canvas {
    id: ribbon
    property var drift: []
    Accessible.role: Accessible.Graphic
    Accessible.name: "Ribbon of the last 30 days. It widens and warms when readings move away from your normal."
    onDriftChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    Connections { target: Theme; function onModeChanged() { ribbon.requestPaint() } }

    function hex(c) { return [parseInt(c.substr(1, 2), 16), parseInt(c.substr(3, 2), 16), parseInt(c.substr(5, 2), 16)] }
    function mix(a, b, t) { return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t] }
    function ramp(stops, s) {
        var p = s * (stops.length - 1), i = Math.min(Math.floor(p), stops.length - 2)
        return mix(stops[i], stops[i + 1], p - i)
    }
    // Smooth the daily scores so the ribbon reads as one form and not as data noise.
    function smoothed(values) {
        return values.map(function (_, i) {
            var total = 0, weight = 0
            for (var j = 0; j < values.length; j++) {
                var w = Math.exp(-(i - j) * (i - j) / 18)
                total += values[j] * w
                weight += w
            }
            return total / weight
        })
    }
    // A cubic curve: in from the right below the top bar, a long sweep, and out at the lower right.
    function point(t) {
        var P = [[1.07, 0.08], [0.02, 0.2], [0.4, 0.88], [1.3, 0.86]], m = 1 - t
        var a = m * m * m, b = 3 * m * m * t, c = 3 * m * t * t, d = t * t * t
        return [width * (a * P[0][0] + b * P[1][0] + c * P[2][0] + d * P[3][0]), height * (a * P[0][1] + b * P[1][1] + c * P[2][1] + d * P[3][1])]
    }

    onPaint: {
        var c = getContext("2d")
        c.reset()
        var strands = 70, segments = 90
        var smooth = smoothed(drift), n = smooth.length
        var cool = Theme.p.ribbonCool.map(hex), warm = Theme.p.ribbonWarm.map(hex), bridge = hex(Theme.p.ribbonWarm[2])
        // Blue to orange turns gray halfway, so the color travels through pink instead.
        function tone(v, heat) {
            var a = ramp(cool, v), b = ramp(warm, v)
            return heat < 0.5 ? mix(a, bridge, heat * 2) : mix(bridge, b, heat * 2 - 1)
        }
        function amount(u) {
            if (!n) return 0
            var p = u * (n - 1), i = Math.floor(p), f = p - i
            var e = f * f * (3 - 2 * f)
            return Math.max(0, Math.min(1, (smooth[i] + (smooth[Math.min(i + 1, n - 1)] - smooth[i]) * e - 25) / 60))
        }
        function thickness(u) { return (70 + 130 * Math.sin(u * Math.PI)) * (1 + 0.9 * amount(u)) }
        function twist(u) { return Math.cos(u * 3.05 + 0.25) }

        c.lineWidth = 3.4
        c.lineCap = "round"
        c.lineJoin = "round"
        c.globalAlpha = 0.92
        for (var s = 0; s <= strands; s++) {
            var v = s / strands
            var path = []
            for (var t = 0; t <= segments; t++) {
                var w = t / segments, here = point(w), next = point(Math.min(w + 0.01, 1)), back = point(Math.max(w - 0.01, 0))
                var dx = next[0] - back[0], dy = next[1] - back[1], len = Math.sqrt(dx * dx + dy * dy) || 1
                var spread = (v - 0.5) * thickness(w) * twist(w)
                path.push([here[0] - dy / len * spread, here[1] + dx / len * spread])
            }
            var g = c.createLinearGradient(path[0][0], path[0][1], path[segments][0], path[segments][1])
            for (var k = 0; k <= 8; k++) {
                var u = k / 8, shade = tone(v, Math.pow(amount(u), 0.8))
                g.addColorStop(u, "rgb(" + Math.round(shade[0]) + "," + Math.round(shade[1]) + "," + Math.round(shade[2]) + ")")
            }
            c.strokeStyle = g
            c.beginPath()
            path.forEach(function (p, i) { i ? c.lineTo(p[0], p[1]) : c.moveTo(p[0], p[1]) })
            c.stroke()
        }
    }
}
