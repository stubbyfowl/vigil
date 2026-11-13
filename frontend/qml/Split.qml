import QtQuick
import QtQuick.Layouts

// Two equal columns. Below stackBelow pixels wide, the second column moves under the first.
GridLayout {
    default property alias first: leftColumn.data
    property alias second: rightColumn.data
    property int stackBelow: 0
    columns: width < stackBelow ? 1 : 2
    columnSpacing: 16
    rowSpacing: 16
    ColumnLayout { id: leftColumn; Layout.fillWidth: true; Layout.preferredWidth: 1; Layout.alignment: Qt.AlignTop; spacing: 12 }
    ColumnLayout { id: rightColumn; Layout.fillWidth: true; Layout.preferredWidth: 1; Layout.alignment: Qt.AlignTop; spacing: 12 }
}
