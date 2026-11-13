import QtQuick
import QtQuick.Layouts

// Blood work as a market feed. It scrolls on its own unless Reduce motion is on, and it can always be dragged.
Rectangle {
    id: ticker
    readonly property var d: Api.ask("lab_ticker", { id: vigil.astronaut, day: vigil.day, v: vigil.version })
    readonly property var items: d.items || []
    visible: items.length > 0
    implicitHeight: 48
    radius: Theme.controlRadius
    color: Theme.panel
    border.width: 1
    border.color: Theme.rule
    Accessible.role: Accessible.StaticText
    Accessible.name: (d.headline || "") + " " + items.map(function (i) { return i.text }).join(" ")

    Placard { id: label; text: "Lab market"; anchors { left: parent.left; leftMargin: 16; verticalCenter: parent.verticalCenter } }
    Rectangle { id: divider; width: 1; color: Theme.rule; anchors { left: label.right; leftMargin: 14; top: parent.top; bottom: parent.bottom; margins: 10 } }

    Flickable {
        id: lane
        anchors { left: divider.right; leftMargin: 14; right: parent.right; rightMargin: 8; top: parent.top; bottom: parent.bottom }
        clip: true
        contentWidth: strip.width
        flickableDirection: Flickable.HorizontalFlick
        boundsBehavior: Flickable.StopAtBounds
        // Two copies side by side, so the feed can loop without a jump.
        Row {
            id: strip
            spacing: 40
            height: lane.height
            Repeater {
                model: ticker.items.concat(ticker.items)
                Row {
                    required property var modelData
                    spacing: 10
                    anchors.verticalCenter: parent.verticalCenter
                    Text { text: modelData.symbol; font.family: Theme.mono; font.weight: Font.Medium; font.pixelSize: 15; font.letterSpacing: 1.2; color: Theme.ink }
                    Text { text: modelData.value; font.family: Theme.body; font.pixelSize: 15; font.features: { "tnum": 1 }; color: Theme.ink }
                    Text {
                        text: modelData.move === "flat" ? "FLAT" : modelData.move === "new" ? "NEW" : modelData.move.toUpperCase() + " " + Math.abs(modelData.change).toFixed(0) + "%"
                        font.family: Theme.mono; font.weight: Font.Medium; font.pixelSize: 14; font.letterSpacing: 1
                        color: modelData.worse ? Theme.warning : Theme.ink2
                    }
                    Text { text: modelData.text; font.family: Theme.body; font.pixelSize: 15; color: Theme.ink2 }
                }
            }
        }
        Timer {
            interval: 40
            repeat: true
            running: ticker.visible && !vigil.reduceMotion && !lane.dragging && !lane.flicking && strip.width > 2 * lane.width
            onTriggered: lane.contentX = (lane.contentX + 1) % (strip.width / 2)
        }
    }
}
