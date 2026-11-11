import QtQuick
import QtQuick.Window

// Mission Control as its own window, with its own sign-in. It sees only what the crew sends.
Window {
    title: "Vigil Mission Control"
    width: 1280
    height: 800
    visible: true
    color: Theme.bg
    Loader {
        anchors.fill: parent
        sourceComponent: vigil.stage === "app" ? controlRoom : signIn
    }
    Component { id: signIn; SignInScreen {} }
    Component { id: controlRoom; GroundScreen { anchors { fill: parent; margins: 24; leftMargin: Theme.gutter; rightMargin: Theme.gutter } standalone: true } }
    LockScreen { anchors.fill: parent; visible: vigil.stage === "app" && vigil.locked; z: 20 }
}
