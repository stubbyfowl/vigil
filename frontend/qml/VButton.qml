import QtQuick
import QtQuick.Controls.Basic

Button {
    id: control
    property string kind: "normal"
    property bool selected: false
    property int textSize: 22
    property int textAlign: Text.AlignHCenter
    implicitHeight: Theme.touch
    implicitWidth: Math.max(Theme.touch, contentItem.implicitWidth + 44)
    focusPolicy: Qt.StrongFocus
    Accessible.name: text
    opacity: enabled ? 1 : 0.55

    contentItem: Text {
        text: control.text
        font.family: Theme.label
        font.pixelSize: control.textSize
        font.letterSpacing: 1.3
        font.capitalization: Font.AllUppercase
        horizontalAlignment: control.textAlign
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
        color: control.selected ? Theme.bg : control.kind === "primary" ? Theme.onAction : control.kind === "danger" ? Theme.warning : Theme.ink
    }
    background: Rectangle {
        radius: 4
        color: control.selected ? Theme.ink : control.kind === "primary" ? Theme.action : Theme.panel2
        border.color: control.visualFocus ? Theme.action : control.kind === "danger" ? Theme.warning : control.selected ? Theme.ink : control.kind === "primary" ? Theme.action : Theme.rule
        border.width: control.visualFocus ? 3 : 1
        scale: control.down ? 0.98 : 1
    }
}
