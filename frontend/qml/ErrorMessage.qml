import QtQuick
import QtQuick.Layouts

ColumnLayout {
    property string text: ""
    spacing: 14
    BackButton {}
    BigTitle { text: "This screen could not load." }
    Body { text: parent.text }
    Item { Layout.fillHeight: true }
}
