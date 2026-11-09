import QtQuick

BorderImage {
    readonly property int spread: 56
    source: "shadow.png"
    visible: Theme.isLight
    z: -1
    anchors { fill: parent; margins: -spread; topMargin: -spread + 6; bottomMargin: -spread - 8 }
    border { left: 76; right: 76; top: 76; bottom: 76 }
}
