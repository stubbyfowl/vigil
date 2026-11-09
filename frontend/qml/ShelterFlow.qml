import QtQuick
import QtQuick.Layouts

// A guided flow, but never a trap: any step can be skipped or gone back to.
ColumnLayout {
    id: flow
    property bool drill: false
    property var storm: null
    property int done: 0
    property real elapsed: 0
    readonly property var steps: [
        "Stop your task. Secure loose items.",
        "Put on your personal dosimeter.",
        "Go to the storm shelter.",
        "Close the hatch. Confirm all crew are inside.",
        "Stay until Vigil shows the all clear."
    ]
    readonly property real timeScale: vigil.delayMinutes * 60 / vigil.flightSeconds
    readonly property real remaining: 7200 - elapsed
    readonly property bool finished: done >= steps.length
    spacing: 8

    function clock(seconds) {
        var s = Math.max(0, Math.floor(seconds))
        return [Math.floor(s / 3600), Math.floor((s % 3600) / 60), s % 60].map(function (p) { return String(p).padStart(2, "0") }).join(":")
    }

    Timer { interval: 250; running: true; repeat: true; onTriggered: flow.elapsed += 0.25 * flow.timeScale }

    RowLayout {
        Layout.fillWidth: true
        Annunciator { status: "red"; label: flow.drill ? "Drill · Shelter now" : "Shelter now" }
        Item { Layout.fillWidth: true }
        Column {
            Placard { anchors.right: parent.right; text: flow.remaining > 0 ? "Spike expected in" : "Storm is here" }
            Text {
                anchors.right: parent.right
                text: flow.clock(flow.remaining)
                font.family: Theme.body; font.bold: true; font.pixelSize: 44; color: Theme.ink
                SequentialAnimation on opacity {
                    running: !flow.finished && !vigil.reduceMotion
                    loops: Animation.Infinite
                    NumberAnimation { to: 0.55; duration: 500 }
                    NumberAnimation { to: 1; duration: 500 }
                }
            }
        }
    }

    Repeater {
        model: flow.steps
        VButton {
            required property int index
            required property string modelData
            Layout.fillWidth: true
            text: (index < flow.done ? "Done  " : (index + 1) + "  ") + modelData
            kind: index === flow.done ? "primary" : "normal"
            enabled: index === flow.done
            textSize: 21
            textAlign: Text.AlignLeft
            onClicked: flow.done = index + 1
        }
    }

    RowLayout {
        Layout.fillWidth: true
        VButton { Layout.fillWidth: true; text: "Back one step"; enabled: flow.done > 0; onClicked: flow.done -= 1 }
        VButton { Layout.fillWidth: true; text: "Skip step"; enabled: !flow.finished; onClicked: flow.done += 1 }
    }

    Body {
        visible: flow.finished
        text: (flow.drill ? "Drill complete. All steps done." : "You are in the shelter.")
            + (flow.storm && flow.storm.shelter_dose_msv !== undefined ? " Dose logged in shelter so far: " + flow.storm.shelter_dose_msv + " mSv. With no shelter: " + flow.storm.unsheltered_dose_msv + " mSv." : "")
    }
}
