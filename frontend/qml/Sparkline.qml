import QtQuick

Canvas {
    id: spark
    property var values: []
    property string label: ""
    property string status: "green"
    implicitHeight: 60
    Accessible.role: Accessible.Graphic
    Accessible.name: label + ". Drift over the last 30 days, now " + (values.length ? values[values.length - 1] : 0) + " of 100."
    onValuesChanged: requestPaint()
    onStatusChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    Connections { target: Theme; function onModeChanged() { spark.requestPaint() } }
    onPaint: {
        var c = getContext("2d")
        c.reset()
        var pad = 3, n = values.length
        c.strokeStyle = Theme.rule
        c.lineWidth = 1
        c.beginPath(); c.moveTo(0, height - 0.5); c.lineTo(width, height - 0.5); c.stroke()
        if (!n) return
        function x(i) { return pad + (n > 1 ? i / (n - 1) * (width - 2 * pad) : 0) }
        function y(v) { return pad + (1 - v / 100) * (height - 2 * pad) }
        var tone = Qt.color(status === "green" ? Theme.band : Theme.statusColor(status))
        var path = function () { c.beginPath(); for (var i = 0; i < n; i++) i ? c.lineTo(x(i), y(values[i])) : c.moveTo(x(i), y(values[i])) }
        path()
        c.lineTo(x(n - 1), height); c.lineTo(x(0), height); c.closePath()
        c.fillStyle = Qt.rgba(tone.r, tone.g, tone.b, 0.12)
        c.fill()
        path()
        c.strokeStyle = tone; c.lineWidth = 2; c.lineJoin = "round"; c.stroke()
    }
}
