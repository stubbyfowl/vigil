import QtQuick
import QtQuick.Layouts

// By default a section is only space and a heading. A surface is for things that stand apart.
Rectangle {
    id: panel
    default property alias content: inner.data
    property string title: ""
    property bool surface: false
    property bool divider: false
    readonly property int pad: surface ? 20 : 0
    color: surface ? Theme.panel : "transparent"
    border.color: surface && !Theme.isLight ? Theme.rule : "transparent"
    border.width: surface && !Theme.isLight ? 1 : 0
    radius: Theme.radius
    implicitHeight: column.implicitHeight + 2 * pad + (divider ? 16 : 0)
    implicitWidth: column.implicitWidth + 2 * pad

    SoftShadow { visible: panel.surface && Theme.isLight }
    Rectangle { visible: panel.divider; anchors { left: parent.left; right: parent.right; top: parent.top } height: 1; color: Theme.rule }

    ColumnLayout {
        id: column
        anchors { left: parent.left; right: parent.right; top: parent.top; margins: panel.pad; topMargin: panel.pad + (panel.divider ? 16 : 0) }
        spacing: 10
        Placard { text: panel.title; visible: panel.title.length > 0; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        ColumnLayout { id: inner; Layout.fillWidth: true; spacing: 8 }
    }
}
