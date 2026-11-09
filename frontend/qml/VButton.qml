import QtQuick
import QtQuick.Controls.Basic

Button {
    id: control
    property string kind: "normal"
    property bool selected: false
    property int textSize: 18
    property int textAlign: Text.AlignHCenter
    implicitHeight: Theme.touch
    implicitWidth: Math.max(Theme.touch, contentItem.implicitWidth + 40)
    focusPolicy: Qt.StrongFocus
    Accessible.name: text
    opacity: enabled ? 1 : 0.5

    contentItem: Text {
        text: control.text
        font.family: Theme.body
        font.weight: Font.Medium
        font.pixelSize: control.textSize
        horizontalAlignment: control.textAlign
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
        color: control.selected ? Theme.actionText : control.kind === "primary" ? Theme.actionText : control.kind === "danger" ? Theme.warning : Theme.ink
    }
    background: Rectangle {
        radius: 9
        color: control.selected || control.kind === "primary" ? Theme.action : control.kind === "quiet" ? "transparent" : Theme.panel
        border.color: control.visualFocus ? Theme.action : control.kind === "quiet" || control.selected || control.kind === "primary" ? "transparent" : Theme.rule
        border.width: control.visualFocus ? 2 : 1
        opacity: control.down ? 0.8 : 1
        Behavior on opacity { enabled: !vigil.reduceMotion; NumberAnimation { duration: 90 } }
    }
}
