import QtQuick
import QtQuick.Window

// Mission Control as its own window, for a second screen.
Window {
    title: "Vigil Mission Control"
    width: 1280
    height: 800
    visible: true
    color: Theme.bg
    GroundScreen { anchors { fill: parent; margins: 24; leftMargin: Theme.gutter; rightMargin: Theme.gutter } standalone: true }
}
