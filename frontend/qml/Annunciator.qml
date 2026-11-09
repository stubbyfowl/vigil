import QtQuick

// A lit legend, like a spacecraft caution panel. Never color alone: always a shape and a word.
Rectangle {
    id: ann
    property string status: "green"
    property string label: Theme.statusWord(status)
    property bool compact: false
    readonly property bool lit: status !== "green"
    readonly property color tint: lit ? Theme.onLit : Theme.nominal
    implicitWidth: row.implicitWidth + (compact ? 14 : 24)
    implicitHeight: compact ? 32 : 36
    radius: 2
    color: lit ? Theme.statusColor(status) : "transparent"
    border.color: lit ? color : Theme.nominal
    Accessible.role: Accessible.StaticText
    Accessible.name: label

    Row {
        id: row
        anchors.centerIn: parent
        spacing: compact ? 5 : 8
        StatusIcon { status: ann.status; tint: ann.tint; anchors.verticalCenter: parent.verticalCenter }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: ann.label
            color: ann.tint
            font.family: Theme.label
            font.pixelSize: ann.compact ? 18 : 20
            font.letterSpacing: ann.compact ? 0.9 : 2
            font.capitalization: Font.AllUppercase
        }
    }

    // A lamp coming on. Once, and only for the most serious state.
    SequentialAnimation on opacity {
        running: ann.status === "red" && !vigil.reduceMotion
        NumberAnimation { to: 0.35; duration: 80 }
        NumberAnimation { to: 1; duration: 80 }
        NumberAnimation { to: 0.6; duration: 40 }
        NumberAnimation { to: 1; duration: 40 }
    }
}
