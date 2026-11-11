import QtQuick

// A plain background. Before sign-in it also shows stars and two transfer orbits, drawn once.
Item {
    id: sky
    property bool decor: false

    Rectangle { anchors.fill: parent; color: Theme.bg }

    Canvas {
        id: art
        anchors.fill: parent
        visible: sky.decor
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onVisibleChanged: requestPaint()
        Connections { target: Theme; function onModeChanged() { art.requestPaint() } }
        onPaint: {
            var c = getContext("2d")
            c.reset()
            var ink = Theme.ink
            if (Theme.stars) {
                var seed = 11
                function rnd() { seed = (seed * 16807) % 2147483647; return seed / 2147483647 }
                for (var i = 0; i < 140; i++) {
                    c.globalAlpha = 0.2 + rnd() * 0.5
                    c.fillStyle = "#ffffff"
                    c.fillRect(rnd() * width, rnd() * height, rnd() < 0.1 ? 2 : 1, rnd() < 0.1 ? 2 : 1)
                }
                c.globalAlpha = 1
            }
            // Earth, Mars, and the path between them, off to the right.
            var cx = width * 1.0, cy = height * 0.6
            c.lineWidth = 1
            c.strokeStyle = Qt.rgba(ink.r, ink.g, ink.b, 0.22)
            c.beginPath(); c.ellipse(cx - 260, cy - 260, 520, 520); c.stroke()
            c.beginPath(); c.ellipse(cx - 430, cy - 430, 860, 860); c.stroke()
            // The transfer orbit, dashed by hand so it works in every renderer.
            c.strokeStyle = Qt.rgba(ink.r, ink.g, ink.b, 0.55)
            for (var a = 0; a < Math.PI * 2; a += 0.05) {
                c.beginPath(); c.arc(cx - 85, cy, 345, a, a + 0.025, false); c.stroke()
            }
            c.fillStyle = Qt.rgba(ink.r, ink.g, ink.b, 0.9)
            c.beginPath(); c.arc(cx - 260 * Math.cos(0.6), cy - 260 * Math.sin(0.6), 6, 0, Math.PI * 2); c.fill()
            c.fillStyle = Theme.urgent
            c.beginPath(); c.arc(cx - 430 * Math.cos(1.1), cy - 430 * Math.sin(1.1), 5, 0, Math.PI * 2); c.fill()
        }
    }
}
