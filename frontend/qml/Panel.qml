import QtQuick
import QtQuick.Layouts

Rectangle {
    id: panel
    default property alias content: inner.data
    property string title: ""
    color: Theme.panel
    border.color: Theme.rule
    radius: 4
    implicitHeight: column.implicitHeight + 28
    implicitWidth: column.implicitWidth + 32

    ColumnLayout {
        id: column
        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 14; leftMargin: 16; rightMargin: 16 }
        spacing: 10
        Placard { text: panel.title; visible: panel.title.length > 0; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        ColumnLayout { id: inner; Layout.fillWidth: true; spacing: 8 }
    }
}
