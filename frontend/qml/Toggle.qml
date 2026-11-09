import QtQuick
import QtQuick.Controls.Basic

CheckBox {
    id: control
    implicitHeight: Theme.touch
    font.family: Theme.body
    font.pixelSize: 18
    Accessible.name: text
    indicator: Rectangle {
        x: 0
        y: (control.height - height) / 2
        width: 34
        height: 34
        radius: 4
        color: control.checked ? Theme.action : Theme.panel2
        border.color: control.visualFocus ? Theme.action : Theme.rule
        border.width: control.visualFocus ? 3 : 1
        StatusIcon { anchors.centerIn: parent; status: "green"; tint: Theme.onAction; visible: control.checked }
    }
    contentItem: Text {
        leftPadding: 46
        text: control.text
        font: control.font
        color: Theme.ink
        verticalAlignment: Text.AlignVCenter
    }
}
