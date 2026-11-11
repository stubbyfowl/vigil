import QtQuick
import QtQuick.Controls.Basic

// primary: the main action. urgent: Earth and emergencies only. normal: outlined. quiet: a text link. danger: outlined in red.
Button {
    id: control
    property string kind: "normal"
    property bool selected: false
    property int textSize: 17
    property int textAlign: Text.AlignHCenter
    readonly property bool filled: kind === "primary" || kind === "urgent" || selected
    implicitHeight: Theme.touch
    implicitWidth: Math.max(Theme.touch, contentItem.implicitWidth + 40)
    focusPolicy: Qt.StrongFocus
    Accessible.name: text
    opacity: enabled ? 1 : 0.4

    contentItem: Text {
        text: control.text
        font.family: Theme.body
        font.weight: Font.DemiBold
        font.pixelSize: control.textSize
        font.underline: control.kind === "quiet" && control.hovered
        horizontalAlignment: control.textAlign
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
        color: control.kind === "urgent" ? Theme.urgentText : control.filled ? Theme.actionText : control.kind === "danger" ? Theme.warning : control.kind === "quiet" ? Theme.link : Theme.ink
    }
    background: Rectangle {
        radius: Theme.controlRadius
        color: control.kind === "urgent" ? Theme.urgent : control.filled ? Theme.action : "transparent"
        border.color: control.visualFocus ? Theme.link : control.filled || control.kind === "quiet" ? "transparent" : control.kind === "danger" ? Theme.warning : Theme.faint(Theme.ink, 0.45)
        border.width: control.visualFocus ? 2 : 1
        opacity: control.down ? 0.75 : 1
        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            color: Theme.faint(Theme.ink, 0.08)
            visible: control.hovered && !control.filled && control.kind !== "quiet"
        }
    }
}
