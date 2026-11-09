import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

ScrollView {
    id: view
    default property alias content: column.data
    contentWidth: availableWidth
    clip: true
    ColumnLayout { id: column; width: view.availableWidth; spacing: 12 }
}
