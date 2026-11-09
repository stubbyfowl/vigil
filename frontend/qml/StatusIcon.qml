import QtQuick

Canvas {
    id: icon
    property string status: "green"
    property color tint: Theme.ink
    implicitWidth: 18
    implicitHeight: 18
    onStatusChanged: requestPaint()
    onTintChanged: requestPaint()
    onPaint: {
        var c = getContext("2d")
        c.reset()
        c.fillStyle = tint
        c.strokeStyle = tint
        c.lineWidth = 3
        c.beginPath()
        if (status === "green") {
            c.moveTo(2, 10); c.lineTo(7, 15); c.lineTo(16, 4); c.stroke()
        } else if (status === "yellow") {
            c.moveTo(9, 2); c.lineTo(17, 16); c.lineTo(1, 16); c.closePath(); c.fill()
        } else {
            c.moveTo(9, 1); c.lineTo(17, 9); c.lineTo(9, 17); c.lineTo(1, 9); c.closePath(); c.fill()
        }
    }
}
