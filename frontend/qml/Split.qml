import QtQuick
import QtQuick.Layouts

// Two equal columns.
RowLayout {
    default property alias first: leftColumn.data
    property alias second: rightColumn.data
    spacing: 16
    ColumnLayout { id: leftColumn; Layout.fillWidth: true; Layout.preferredWidth: 1; Layout.alignment: Qt.AlignTop; spacing: 12 }
    ColumnLayout { id: rightColumn; Layout.fillWidth: true; Layout.preferredWidth: 1; Layout.alignment: Qt.AlignTop; spacing: 12 }
}
