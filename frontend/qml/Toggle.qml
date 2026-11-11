import QtQuick
import QtQuick.Controls.Basic

Switch {
    id: control
    implicitHeight: Theme.touch
    font.family: Theme.body
    font.pixelSize: 18
    Accessible.name: text
    indicator: Rectangle {
        x: 0
        y: (control.height - height) / 2
        width: 48
        height: 28
        radius: 14
        color: control.checked ? Theme.nominal : Theme.panel2
        border.color: control.visualFocus ? Theme.action : control.checked ? Theme.action : Theme.rule
        Rectangle {
            x: control.checked ? parent.width - width - 3 : 3
            y: 3
            width: 22
            height: 22
            radius: 11
            color: control.checked ? Theme.actionText : Theme.ink2
            Behavior on x { enabled: !vigil.reduceMotion; NumberAnimation { duration: 120 } }
        }
    }
    contentItem: Text {
        leftPadding: 60
        text: control.text
        font: control.font
        color: Theme.ink
        verticalAlignment: Text.AlignVCenter
    }
}
