import QtQuick
import QtQuick.Layouts

Item {
    id: screen
    property string phase: "idle"
    property real minutes: 0
    property int steps: 0
    readonly property int oneWay: vigil.delayMinutes
    readonly property real secondsPerMinute: vigil.flightSeconds / vigil.delayMinutes
    readonly property int thinkMinutes: 5
    readonly property int total: oneWay * 2 + thinkMinutes
    readonly property bool outbound: minutes <= oneWay
    readonly property bool thinking: minutes > oneWay && minutes <= oneWay + thinkMinutes
    readonly property bool done: minutes >= total
    readonly property var vigilSteps: ["Compared today with your own normal", "Wrote a plain-language alert", "Started the self-care step", "Told the Medical Officer", "Queued a summary for Earth"]
    readonly property real position: phase !== "waiting" ? 0 : outbound ? minutes / oneWay : thinking ? 1 : 1 - (minutes - oneWay - thinkMinutes) / oneWay

    function start(next) { minutes = 0; steps = 0; phase = next }
    function mmss(m) { return String(Math.floor(m)).padStart(2, "0") + ":" + String(Math.floor((m % 1) * 60)).padStart(2, "0") }

    Timer {
        interval: 80
        repeat: true
        running: screen.phase === "waiting" && !screen.done
        onTriggered: screen.minutes = Math.min(screen.total, screen.minutes + 0.08 / screen.secondsPerMinute)
    }
    Timer {
        interval: 280
        repeat: true
        running: screen.phase === "vigil" && screen.steps < screen.vigilSteps.length
        onTriggered: screen.steps += 1
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 12
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            BackButton {}
            BigTitle { text: "Delay Theater" }
            Item { Layout.fillWidth: true }
            VButton { text: "Wait for Earth"; onClicked: screen.start("waiting") }
            VButton { kind: "primary"; text: "Use Vigil"; onClicked: screen.start("vigil") }
        }
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 12
            Panel {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredWidth: 1
                surface: true
                title: "Astronaut"
                Body {
                    font.pixelSize: 24
                    font.weight: Font.Medium
                    visible: screen.phase !== "vigil"
                    text: screen.phase === "idle" ? "Resting heart rate is up. Sleep is down. Is this serious? Choose how to find out." : screen.done ? "Reply received. The condition had time to change." : "Waiting for Earth. No guidance yet."
                }
                Text { visible: screen.phase === "waiting"; text: screen.mmss(screen.minutes); font.family: Theme.body; font.weight: Font.DemiBold; font.pixelSize: 96; font.letterSpacing: -3; font.features: { "tnum": 1 }; color: Theme.ink }
                Note { visible: screen.phase === "waiting"; text: "Time since asking" }
                Repeater {
                    model: screen.phase === "vigil" ? screen.vigilSteps : []
                    RowLayout {
                        required property string modelData
                        required property int index
                        spacing: 10
                        Text { text: index < screen.steps ? "Done" : "..."; font.family: Theme.body; font.features: { "tnum": 1 }; font.pixelSize: 20; color: index < screen.steps ? Theme.nominal : Theme.ink2; Layout.preferredWidth: 60 }
                        Body { text: modelData; font.pixelSize: 20; color: index < screen.steps ? Theme.ink : Theme.ink2 }
                    }
                }
                StatusPill { visible: screen.phase === "vigil" && screen.steps === screen.vigilSteps.length; status: "green"; label: "Acting now, no wait" }
            }
            ColumnLayout {
                Layout.fillWidth: false
                Layout.minimumWidth: 170
                Layout.maximumWidth: 170
                spacing: 12
                Layout.alignment: Qt.AlignVCenter
                Placard { Layout.alignment: Qt.AlignHCenter; text: screen.oneWay + " min one way" }
                Rectangle {
                    id: track
                    Layout.fillWidth: true
                    implicitHeight: 2
                    color: Theme.rule
                    Rectangle {
                        visible: screen.phase === "waiting" && !screen.thinking && !screen.done
                        x: screen.position * track.width - 9
                        y: -8
                        width: 18
                        height: 18
                        radius: 9
                        color: Theme.flag
                    }
                }
            }
            Panel {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredWidth: 1
                surface: true
                title: "Ground"
                Body {
                    font.pixelSize: 24
                    font.weight: Font.Medium
                    text: screen.phase === "idle" ? "Earth has no idea yet."
                        : screen.phase === "vigil" ? "A summary will arrive in " + screen.oneWay + " minutes. The astronaut already has a plan."
                        : screen.outbound ? "Message in transit." : screen.thinking ? "Flight surgeon reviews the data." : screen.done ? "Reply delivered." : "Reply in transit."
                }
            }
        }
        Note { text: "A model of the delay, using the configured " + screen.oneWay + " minutes one way. This demo plays " + screen.oneWay + " minutes as " + Math.round(screen.oneWay * screen.secondsPerMinute) + " seconds." }
    }
}
