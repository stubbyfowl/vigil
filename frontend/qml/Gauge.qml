import QtQuick

// A dial from 0 to 100 drift, with ticks like an instrument. The number in the middle is the same value.
Item {
    id: gauge
    property real value: 0
    property string status: "green"
    property bool learning: false
    property int size: 120
    property int thickness: Math.max(5, Math.round(size * 0.06))
    property string label: ""
    property bool showNumber: true
    property int numberSize: Math.round(size * 0.3)
    property real shown: 0
    implicitWidth: size
    implicitHeight: size
    Accessible.role: Accessible.Graphic
    Accessible.name: label + (learning ? ". No baseline yet." : ". Drift " + Math.round(value) + " of 100, " + Theme.statusWord(status) + ".")

    function settle() { shown = learning ? 0 : Math.max(0, Math.min(100, value)) }
    Component.onCompleted: settle()
    onValueChanged: settle()
    onLearningChanged: settle()
    Behavior on shown { enabled: !vigil.reduceMotion; NumberAnimation { duration: 700; easing.type: Easing.OutCubic } }

    Canvas {
        id: dial
        anchors.fill: parent
        property real v: gauge.shown
        onVChanged: requestPaint()
        Connections { target: Theme; function onModeChanged() { dial.requestPaint() } }
        Connections { target: gauge; function onStatusChanged() { dial.requestPaint() } }
        onPaint: {
            var c = getContext("2d")
            c.reset()
            var r = width / 2 - gauge.thickness - 8, cx = width / 2, cy = height / 2
            var start = Math.PI * 0.75, sweep = Math.PI * 1.5
            // Ticks every 25.
            c.strokeStyle = Theme.ink2
            c.lineWidth = 1.5
            for (var t = 0; t <= 4; t++) {
                var a = start + sweep * t / 4
                c.beginPath()
                c.moveTo(cx + Math.cos(a) * (r + gauge.thickness / 2 + 3), cy + Math.sin(a) * (r + gauge.thickness / 2 + 3))
                c.lineTo(cx + Math.cos(a) * (r + gauge.thickness / 2 + 8), cy + Math.sin(a) * (r + gauge.thickness / 2 + 8))
                c.stroke()
            }
            c.lineCap = "butt"
            c.lineWidth = gauge.thickness
            c.strokeStyle = Theme.rule
            c.beginPath(); c.arc(cx, cy, r, start, start + sweep, false); c.stroke()
            if (v < 0.5) return
            c.strokeStyle = gauge.status === "green" ? Theme.band : Theme.statusColor(gauge.status)
            c.beginPath(); c.arc(cx, cy, r, start, start + sweep * v / 100, false); c.stroke()
        }
    }
    Text {
        anchors.centerIn: parent
        visible: gauge.showNumber && !gauge.learning
        text: Math.round(gauge.shown)
        font.family: Theme.display
        font.weight: Font.ExtraBold
        font.pixelSize: gauge.numberSize
        font.letterSpacing: -gauge.numberSize * 0.03
        font.features: { "tnum": 1 }
        color: Theme.ink
    }
    Placard {
        anchors.centerIn: parent
        visible: gauge.learning && gauge.showNumber
        text: "No baseline"
        font.pixelSize: Math.max(10, Math.min(13, gauge.size * 0.09))
        font.letterSpacing: 1.2
    }
}
