import QtQuick
import QtQuick.Layouts

// A section is space and a label. A surface is a card with a hairline border.
Rectangle {
    id: panel
    default property alias content: inner.data
    property string title: ""
    property bool surface: false
    property bool divider: false
    property color glow: "transparent"
    readonly property int pad: surface ? 22 : 0
    color: surface ? Theme.panel : "transparent"
    border.color: surface ? (panel.glow.a > 0 ? panel.glow : Theme.rule) : "transparent"
    border.width: surface ? 1 : 0
    radius: Theme.radius
    implicitHeight: column.implicitHeight + 2 * pad + (divider ? 16 : 0)
    implicitWidth: column.implicitWidth + 2 * pad

    SoftShadow { visible: panel.surface && Theme.isLight }
    Rectangle { visible: panel.divider; anchors { left: parent.left; right: parent.right; top: parent.top } height: 1; color: Theme.rule }

    ColumnLayout {
        id: column
        anchors { left: parent.left; right: parent.right; top: parent.top; margins: panel.pad; topMargin: panel.pad + (panel.divider ? 16 : 0) }
        spacing: 12
        Placard { text: panel.title; visible: panel.title.length > 0; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        ColumnLayout { id: inner; Layout.fillWidth: true; spacing: 8 }
    }
}
