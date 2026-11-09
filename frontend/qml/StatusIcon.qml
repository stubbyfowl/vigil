import QtQuick

Canvas {
    id: icon
    property string status: "green"
    property color tint: Theme.ink
    implicitWidth: 16
    implicitHeight: 16
    onStatusChanged: requestPaint()
    onTintChanged: requestPaint()
    onPaint: {
        var c = getContext("2d")
        c.reset()
        c.fillStyle = tint
        c.strokeStyle = tint
        c.lineWidth = 2.4
        c.lineCap = "round"
        c.lineJoin = "round"
        c.beginPath()
        if (status === "green") {
            c.moveTo(2, 8.5); c.lineTo(6.2, 12.5); c.lineTo(14, 3.5); c.stroke()
        } else if (status === "yellow") {
            c.moveTo(8, 2); c.lineTo(15, 14); c.lineTo(1, 14); c.closePath(); c.fill(); c.stroke()
        } else {
            c.moveTo(8, 1); c.lineTo(15, 8); c.lineTo(8, 15); c.lineTo(1, 8); c.closePath(); c.fill(); c.stroke()
        }
    }
}
