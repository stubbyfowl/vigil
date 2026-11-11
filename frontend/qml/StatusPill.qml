import QtQuick

// A status tag, after nasa.gov's LIVE box: an outlined label with a shape and a word. It is not a button.
Rectangle {
    id: tag
    property string status: "green"
    property string label: Theme.statusWord(status)
    property bool compact: false
    readonly property bool neutral: status === "none"
    readonly property color tone: neutral ? Theme.ink2 : Theme.statusColor(status)
    implicitWidth: row.implicitWidth + 18
    implicitHeight: compact ? 28 : 32
    radius: 2
    color: "transparent"
    border.width: 1
    border.color: tone
    Accessible.role: Accessible.StaticText
    Accessible.name: label

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 7
        StatusIcon { visible: !tag.neutral; status: tag.status; tint: tag.tone; anchors.verticalCenter: parent.verticalCenter; implicitWidth: 13; implicitHeight: 13; scale: 0.8 }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: tag.label
            color: tag.tone
            font.family: Theme.mono
            font.weight: Font.Medium
            font.pixelSize: 13
            font.letterSpacing: 1.8
            font.capitalization: Font.AllUppercase
        }
    }
}
