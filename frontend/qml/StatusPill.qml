import QtQuick

// Status is never color alone: always a shape and a word.
Rectangle {
    id: pill
    property string status: "green"
    property string label: Theme.statusWord(status)
    property bool compact: false
    implicitWidth: row.implicitWidth + (compact ? 18 : 24)
    implicitHeight: compact ? 30 : 34
    radius: height / 2
    color: Theme.statusFill(status)
    Accessible.role: Accessible.StaticText
    Accessible.name: label

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 6
        StatusIcon { status: pill.status; tint: Theme.statusColor(pill.status); anchors.verticalCenter: parent.verticalCenter; implicitWidth: 14; implicitHeight: 14; scale: 0.8 }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: pill.label
            color: Theme.statusColor(pill.status)
            font.family: Theme.body
            font.weight: Font.Medium
            font.pixelSize: 16
        }
    }
}
