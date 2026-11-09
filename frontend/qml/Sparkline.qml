import QtQuick

Canvas {
    id: spark
    property var values: []
    property string label: ""
    implicitHeight: 72
    Accessible.role: Accessible.Graphic
    Accessible.name: label + ". 30-day drift trend, latest " + (values.length ? values[values.length - 1] : 0) + " of 100."
    onValuesChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    Connections { target: vigil; function onPrefsChanged() { spark.requestPaint() } }
    onPaint: {
        var c = getContext("2d")
        c.reset()
        var pad = 7, n = values.length
        function x(i) { return pad + (n > 1 ? i / (n - 1) * (width - 2 * pad) : 0) }
        function y(v) { return pad + (1 - v / 100) * (height - 2 * pad) }
        c.strokeStyle = Theme.rule
        c.globalAlpha = 0.45
        c.lineWidth = 1
        ;[30, 60].forEach(function (g) { c.beginPath(); c.moveTo(pad, y(g)); c.lineTo(width - pad, y(g)); c.stroke() })
        c.globalAlpha = 1
        if (!n) return
        c.strokeStyle = Theme.ink
        c.lineWidth = 2
        c.lineJoin = "round"
        c.beginPath()
        for (var i = 0; i < n; i++) i ? c.lineTo(x(i), y(values[i])) : c.moveTo(x(i), y(values[i]))
        c.stroke()
        c.fillStyle = Theme.ink
        c.beginPath()
        c.arc(x(n - 1), y(values[n - 1]), 5, 0, Math.PI * 2)
        c.fill()
    }
}
